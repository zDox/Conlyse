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
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        n_folds=args.folds,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        device=args.device,
    )


def _cmd_eval(args: argparse.Namespace) -> None:
    from torch.utils.data import DataLoader

    from .data.dataset import GnnWinDataset, collate_fn
    from .predict import load_model
    from .train import evaluate

    dataset = GnnWinDataset(args.dataset_dir)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, collate_fn=collate_fn)
    model = load_model(args.checkpoint, device=args.device)

    metrics = evaluate(model, loader, args.device)
    print(f"Games: {len(dataset):,}")
    for key, value in metrics.items():
        print(f"{key:>16}: {value:.4f}")


def _cmd_report(args: argparse.Namespace) -> None:
    from .report import generate_report

    generate_report(
        dataset_dir=args.dataset_dir,
        checkpoint_path=args.checkpoint,
        output_path=args.output,
        batch_size=args.batch_size,
        device=args.device,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="conlyse-predict — GNN + Transformer win-predictor for Conflict of Nations",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── train ──────────────────────────────────────────────────────────────
    train_p = sub.add_parser("train", help="Train the GNN + Transformer win predictor")
    train_p.add_argument(
        "--dataset-dir", required=True, type=Path, help="Directory of game_<id>.pt files (from gnn-extract)"
    )
    train_p.add_argument("--output-dir", required=True, type=Path, help="Output directory for win_predictor.pt")
    train_p.add_argument("--folds", type=int, default=5, help="Number of KFold cross-validation folds (default: 5)")
    train_p.add_argument("--epochs", type=int, default=20, help="Training epochs per fold (default: 20)")
    train_p.add_argument("--batch-size", type=int, default=4, help="Batch size in games (default: 4)")
    train_p.add_argument("--lr", type=float, default=1e-4, help="Learning rate (default: 1e-4)")
    train_p.add_argument("--device", default="cpu", help="torch device (default: cpu)")
    _add_common_args(train_p)

    # ── eval ───────────────────────────────────────────────────────────────
    eval_p = sub.add_parser("eval", help="Evaluate a checkpoint and print metrics")
    eval_p.add_argument("--dataset-dir", required=True, type=Path, help="Directory of game_<id>.pt files")
    eval_p.add_argument("--checkpoint", required=True, type=Path, help="Trained checkpoint (win_predictor.pt)")
    eval_p.add_argument("--batch-size", type=int, default=4, help="Batch size in games (default: 4)")
    eval_p.add_argument("--device", default="cpu", help="torch device (default: cpu)")
    _add_common_args(eval_p)

    # ── report ─────────────────────────────────────────────────────────────
    report_p = sub.add_parser("report", help="Generate a detailed HTML evaluation report (charts + diagnostics)")
    report_p.add_argument("--dataset-dir", required=True, type=Path, help="Directory of game_<id>.pt files")
    report_p.add_argument("--checkpoint", required=True, type=Path, help="Trained checkpoint (win_predictor.pt)")
    report_p.add_argument("--output", required=True, type=Path, help="Output HTML report path (e.g. report.html)")
    report_p.add_argument("--batch-size", type=int, default=4, help="Batch size in games (default: 4)")
    report_p.add_argument("--device", default="cpu", help="torch device (default: cpu)")
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
