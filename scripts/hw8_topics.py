from confluent_kafka.admin import AdminClient, NewTopic

from hw8_kafka import BROKER, DEAD, DRAFTS, FINAL, INBOX, REQUESTS, RESPONSES, TASKS


def main():
    admin = AdminClient({"bootstrap.servers": BROKER})
    topics = {REQUESTS: 1, RESPONSES: 1, INBOX: 1, TASKS: 2, DRAFTS: 1, FINAL: 1, DEAD: 1}
    existing = admin.list_topics(timeout=15).topics
    futures = admin.create_topics([NewTopic(name, partitions, 1) for name, partitions in topics.items() if name not in existing])
    for name, future in futures.items():
        future.result()
        print("CREATED", name)
    metadata = admin.list_topics(timeout=15)
    for name, partitions in topics.items():
        actual = len(metadata.topics[name].partitions)
        assert actual == partitions, (name, actual, partitions)
        print(name, "partitions=", actual)


if __name__ == "__main__":
    main()
