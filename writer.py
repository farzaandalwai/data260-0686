from hw8_kafka import DRAFTS, TASKS
from hw8_pipeline import run_stage, write


if __name__ == "__main__":
    run_stage("writer", TASKS, DRAFTS, write)
