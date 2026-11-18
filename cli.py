import sys
import asyncio
import argparse
import json
import os
from services.analyzer import run_analysis_flow

_RUN_DIR = None

async def main():
    # 커맨드라인 인자 설정
    parser = argparse.ArgumentParser(description="웹 UI/UX 및 코드 품질 자동 검수 CLI (CI/CD용)")
    parser.add_argument("--url", required=True, help="분석할 웹사이트의 메인 URL")
    parser.add_argument("--threshold", type=int, default=70, help="빌드 통과를 위한 최소 점수 커트라인 (기본값: 70)")
    parser.add_argument("--output", default="audit_report.json", help="결과 리포트를 저장할 JSON 파일 경로")
    parser.add_argument("--pdf", nargs="*", default=[], help="추가 분석용 가이드라인 PDF 파일 경로 리스트")
    # --- 실험용 플래그 (기본값은 기존 동작과 같다) ---
    from services import exp_config as ec
    parser.add_argument("--max-pages", type=int, default=ec.DEFAULT_MAX_PAGES,
                        help="분석할 최대 페이지 수 (시작 페이지 포함). 1이면 시작 페이지만 (기본 5)")
    parser.add_argument("--no-rag", action="store_true", help="가이드라인 섹션 제목은 두고 내용을 비운다")
    parser.add_argument("--modality", choices=ec.MODALITIES, default="both")
    parser.add_argument("--viewport-extra", choices=["mobile"], default=None,
                        help="mobile: 뷰포트를 390x844 로 바꾼다 (기본 1280x800)")
    parser.add_argument("--query-mode", choices=ec.QUERY_MODES, default="fixed")
    parser.add_argument("--oracle-chunks", default=None, help="oracle 모드: page_id,chunk_id CSV")
    parser.add_argument("--page-id", default=None, help="oracle 모드/로그용 페이지 ID (예: page_001)")
    parser.add_argument("--chroma-path", default=ec.DEFAULT_CHROMA_PATH)
    parser.add_argument("--prompt-date", default=None, help="프롬프트 날짜 고정 YYYY-MM-DD (기본: 실행 당일)")
    parser.add_argument("--run-id", default=None, help="지정하면 results/revision/runs/{run_id}/ 에 호출 로그를 남긴다")
    parser.add_argument("--concurrency", type=int, default=None, help="사이트 내 페이지 동시 분석 수 (기본 제한 없음)")

    args = parser.parse_args()

    config = None
    experimental = (args.max_pages != ec.DEFAULT_MAX_PAGES or args.no_rag or args.modality != "both"
                    or args.viewport_extra or args.query_mode != "fixed" or args.chroma_path != ec.DEFAULT_CHROMA_PATH
                    or args.prompt_date or args.run_id or args.concurrency or args.page_id)
    run_dir = None
    if experimental:
        from services import llm_wrapper as lw
        oracle = {}
        if args.oracle_chunks:
            import csv
            with open(args.oracle_chunks, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    oracle.setdefault(r["page_id"], []).append(r["chunk_id"])
        config = ec.ExperimentConfig(
            run_id=args.run_id, condition="cli", max_pages=args.max_pages, rag=not args.no_rag,
            modality=args.modality,
            viewport=ec.MOBILE_VIEWPORT if args.viewport_extra == "mobile" else ec.DEFAULT_VIEWPORT,
            query_mode=args.query_mode, oracle_chunks=oracle, chroma_path=args.chroma_path,
            prompt_date=args.prompt_date, concurrency=args.concurrency, page_id=args.page_id,
            require_rag_chunks=args.chroma_path != ec.DEFAULT_CHROMA_PATH,
        ).validate()
        if args.run_id:
            run_dir = lw.create_run_dir(os.path.join("results", "revision", "runs"), args.run_id)
            config.logger = lw.RunLogger(run_dir, args.run_id)
            config.shots_dir = os.path.join(run_dir, "shots")
            global _RUN_DIR
            _RUN_DIR = run_dir

    print("="*60)
    print(f"[CI/CD Automated Audit] 파이프라인 가동")
    print(f"Target URL: {args.url}")
    print(f"Threshold (최소 통과 점수): {args.threshold}점")
    print("="*60 + "\n")

    final_result = None

    # 분석 엔진 구동 및 실시간 상태 모니터링
    try:
        async for step in run_analysis_flow(target_url=args.url, is_any_checked=args.pdf, upload_file=[],
                                            config=config):
            
            # 진행 상태 텍스트 출력 (CI/CD 로그용)
            if step.get("text"):
                progress = step.get("progress", 0)
                if progress >= 0:
                    print(f"⏳ [진행률 {progress}%] {step['text']}")
                else:
                    print(f"⚠️ {step['text']}")
            
            # 최종 결과 데이터 포착
            if "result" in step:
                final_result = step["result"]

    except Exception as e:
        print(f"\n[FATAL ERROR] 분석 프로세스 중 치명적 오류가 발생했습니다: {e}")
        sys.exit(1)

    # 결과 검증 및 빌드 락(Lock) 처리
    if not final_result or final_result.get("status") == "error":
        error_msg = final_result.get("message", "원인을 알 수 없는 오류") if final_result else "결과 데이터를 받지 못했습니다."
        print(f"\n[BUILD FAIL] 분석 실패: {error_msg}")
        sys.exit(1)

    # CI/CD 아티팩트용 JSON 파일 저장
    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        print(f"\n📄 전체 분석 결과가 리포트 파일로 저장되었습니다: {os.path.abspath(args.output)}")
    except Exception as e:
        print(f"\nJSON 리포트 파일 저장 중 오류 발생: {e}")

    # 점수 기반 통과 여부 판별
    scores = final_result.get("scores", {})
    if not scores:
        print("\n[BUILD FAIL] 산출된 점수 데이터가 없습니다.")
        sys.exit(1)

    print("\n카테고리별 검수 점수:")
    for category, score in scores.items():
        print(f"   - {category}: {score}점")

    min_score = min(scores.values())
    
    print("\n" + "="*60)
    if min_score < args.threshold:
        print(f"[ACTION REQUIRED] 배포 차단 (Build Locked)")
        print(f"이유: 최저 점수({min_score}점)가 설정된 기준치({args.threshold}점)에 미달합니다.")
        print("="*60)
        sys.exit(1)  # Exit Code 1: 실패
    else:
        print(f"[SUCCESS] 모든 품질 검사를 통과했습니다. 배포를 계속 진행합니다.")
        print("="*60)
        sys.exit(0)  # Exit Code 0: 성공

if __name__ == "__main__":
    # Windows 환경에서 Playwright 비동기 오류 방지를 위한 정책 설정
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    finally:
        if _RUN_DIR:
            from services.llm_wrapper import lock_run
            lock_run(_RUN_DIR)