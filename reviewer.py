from hw8_kafka import DRAFTS, FINAL
from hw8_pipeline import review, run_stage


if __name__ == "__main__":
    run_stage("reviewer", DRAFTS, FINAL, review)
