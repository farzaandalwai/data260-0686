from hw8_kafka import INBOX, TASKS
from hw8_pipeline import plan, run_stage


if __name__ == "__main__":
    run_stage("planner", INBOX, TASKS, plan)
