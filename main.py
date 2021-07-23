import os
import argparse
from grind_search import grind


def parse_module():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", "-m", nargs="+", choices=["incept", "xept", "effnet0", "effnet1"], default="effnet0", help="Select pretrained model.")
    parser.add_argument("--optimizer", "-opt", nargs="+", required=True, choices=["adam", "ftrl", "sgd", "rmsprop", "adadelta", "adagrad", "adamax", "nadam"], type=str, help="Select optimizer.")
    parser.add_argument("--image_size", "-is", nargs="+", required=True, type=int, help="Select image size.")
    parser.add_argument("--image_type", "-it", nargs="+", required=True, type=str, choices=["derm", "clinic", "both"], help="Select image type to use during training.")
    parser.add_argument("--colour", "-clr", nargs="+", required=True, type=str, help="Select image size.")
    parser.add_argument("--batch-size", "-btch", nargs="+", required=True, type=int, help="Select batch size.")
    parser.add_argument("--learning-rate", "-lr", nargs="+", required=True, type=float, help="Select learning rate.")
    parser.add_argument("--dropout-rate", "-dor", nargs="+", required=True, type=float, help="Select dropout rate.")
    parser.add_argument("--relu-grad", "-rg", nargs="+", required=True, type=float, help="Select leaky relu gradient.")
    parser.add_argument("--dataset-frac", "-frac", default=1., type=float, help="Dataset fraction.")
    parser.add_argument("--epochs", "-e", required=True, type=int, help="Select epochs.")
    parser.add_argument("--early-stop", "-es", required=True, type=int, help="Select early stop epochs.")
    parser.add_argument("--nodes", "-nod", required=True, type=str, choices=["multi", "one"], help="Select training nodes.")
    parser.add_argument("--mode", "-mod", required=True, type=str, choices=["5cls", "ben_mal", "nev_mel"], help="Select the type of outputs.")
    parser.add_argument("--verbose", "-v", action="count", default=0, help="Set verbosity.")
    return parser


if __name__ == "__main__":
    args = parse_module().parse_args().__dict__
    os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
    os.environ["TF_GPU_THREAD_MODE"] = "gpu_private"
    # Set verbose for TF CPP LOG
    # 0 = all logs, 1 = filter out INFO, 2 = 1 + WARNING, 3 = 2 + ERROR
    if args["verbose"] > 3:
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "0"
    else:
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = f"{3 - args['verbose']}"
    # Set verbose for keras
    if args["verbose"] == 1:
        args["verbose"] = 2
    elif args["verbose"] >= 2:
        args["verbose"] = 1
    else:
        args["verbose"] = 0
    grind(args=args)
