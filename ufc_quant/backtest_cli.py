"""CLI for temporal CSV backtest."""
import argparse
from .backtest import temporal_backtest, save_result
def main():
    ap=argparse.ArgumentParser(description="Temporal logistic-regression UFC bout backtest")
    ap.add_argument("csv")
    ap.add_argument("--features",required=True,help="Comma-separated pre-fight feature columns")
    ap.add_argument("--outcome",default="y")
    ap.add_argument("--date",default="date")
    ap.add_argument("--train-fraction",type=float,default=0.7)
    ap.add_argument("--output",default="backtest_result.json")
    a=ap.parse_args()
    result=temporal_backtest(a.csv,a.features.split(","),a.outcome,a.date,a.train_fraction)
    save_result(result,a.output)
    print(result["metrics"])
    print("Saved:",a.output)
if __name__=="__main__": main()
