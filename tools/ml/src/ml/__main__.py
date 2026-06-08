"""CLI entry point for conlyse-predict."""

import argparse
import logging
import sys
from pathlib import Path


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show ERROR messages")


def _configure_logging(args: argparse.Namespace) -> None:
    level = logging.DEBUG if args.verbose else (logging.ERROR if args.quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _cmd_train(args: argparse.Namespace) -> None:
    from .train import train

    train(
        dataset_path=args.dataset,
        output_path=args.output,
        n_folds=args.folds,
        min_coverage=args.min_coverage,
    )


def _cmd_eval(args: argparse.Namespace) -> None:
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score

    from .features import load_dataset

    logger = logging.getLogger(__name__)
    logger.info("Loading dataset from %s", args.dataset)
    df = load_dataset(args.dataset)

    if args.min_coverage > 1:
        df = df[df["bucket_coverage"] >= args.min_coverage].reset_index(drop=True)

    model = lgb.Booster(model_file=str(args.model))
    cols = model.feature_name()

    for col in cols:
        if col not in df.columns:
            df[col] = 0.0

    X = df[cols].values
    y = df["is_winner"].astype(int).values
    preds = model.predict(X)

    overall_auc = roc_auc_score(y, preds)
    print(f"Overall AUC: {overall_auc:.4f}  (n={len(df):,})")
    print()
    print(f"{'pct_game':>8}  {'n':>8}  {'AUC':>8}  {'pos_rate':>10}")
    print("-" * 42)
    for pct in sorted(df["pct_game"].unique()):
        mask = df["pct_game"].values == pct
        if mask.sum() < 10:
            continue
        auc = roc_auc_score(y[mask], preds[mask])
        pos_rate = y[mask].mean()
        print(f"{pct:8d}  {mask.sum():8,}  {auc:8.4f}  {pos_rate:10.4f}")


def _cmd_report(args: argparse.Namespace) -> None:
    from .report import generate_report

    generate_report(
        dataset_path=args.dataset,
        model_path=args.model,
        output_path=args.output,
        min_coverage=args.min_coverage,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="conlyse-predict — win-probability ML for Conflict of Nations",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── train ──────────────────────────────────────────────────────────────
    train_p = sub.add_parser("train", help="Train LightGBM win-probability model")
    train_p.add_argument(
        "--dataset",
        required=True,
        type=Path,
        help="Parquet training dataset (from game-stats-extractor ml-dataset)",
    )
    train_p.add_argument(
        "--output", required=True, type=Path, help="Output model file (e.g. model.lgb)"
    )
    train_p.add_argument(
        "--folds",
        type=int,
        default=5,
        help="Number of GroupKFold cross-validation folds (default: 5)",
    )
    train_p.add_argument(
        "--min-coverage",
        type=int,
        default=1,
        metavar="N",
        help="Minimum bucket_coverage to include a row (default: 1)",
    )
    _add_common_args(train_p)

    # ── eval ───────────────────────────────────────────────────────────────
    eval_p = sub.add_parser("eval", help="Evaluate model AUC by pct_game bucket")
    eval_p.add_argument(
        "--dataset", required=True, type=Path, help="Parquet dataset to evaluate on"
    )
    eval_p.add_argument("--model", required=True, type=Path, help="Trained model file (.lgb)")
    eval_p.add_argument(
        "--min-coverage",
        type=int,
        default=1,
        metavar="N",
        help="Minimum bucket_coverage to include a row (default: 1)",
    )
    _add_common_args(eval_p)

    # ── report ─────────────────────────────────────────────────────────────
    report_p = sub.add_parser(
        "report", help="Generate a detailed HTML evaluation report (charts + diagnostics)"
    )
    report_p.add_argument(
        "--dataset", required=True, type=Path, help="Parquet dataset to evaluate on"
    )
    report_p.add_argument("--model", required=True, type=Path, help="Trained model file (.lgb)")
    report_p.add_argument(
        "--output", required=True, type=Path, help="Output HTML report path (e.g. report.html)"
    )
    report_p.add_argument(
        "--min-coverage",
        type=int,
        default=1,
        metavar="N",
        help="Minimum bucket_coverage to include a row (default: 1)",
    )
    _add_common_args(report_p)

    args = parser.parse_args()
    _configure_logging(args)

    try:
        if args.command == "train":
            _cmd_train(args)
        elif args.command == "eval":
            _cmd_eval(args)
        elif args.command == "report":
            _cmd_report(args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        logging.getLogger(__name__).exception("Command failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
