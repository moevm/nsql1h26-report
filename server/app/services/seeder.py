import hashlib
import logging
import time
from typing import List, Dict

from server.app.database import run_query, run_write

logger = logging.getLogger(__name__)


def make_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_chunk(text: str) -> Dict:
    return {"text": text, "hash": make_hash(text)}


SHARED_CHUNKS = [
    "Целью данной работы является создание программы для обработки PNG-изображений с использованием командной строки (CLI).",
    "Программа должна будет обеспечивать проверку соответствия файлов формату BMP.",
    "Для достижения цели необходимо выполнить следующие задачи: изучение формата BMP, разработка CLI для взаимодействия с пользователем.",
    "Реализация функций для обработки изображений, включая замену параметров RGB у пикселя.",
    "Обеспечение проверки BMP-формата и корректной обработки ошибок.",
]

COMMON_CONCLUSION = [
    "В ходе выполнения лабораторной работы были достигнуты все поставленные цели и задачи.",
    "Разработанная программа прошла тестирование на различных входных данных и показала корректные результаты.",
    "Все функции реализованы в соответствии с техническим заданием.",
]

SEED_DATA = {
    "students": [
        {"id": 1, "name": "Иван",    "surname": "Иванов",   "group": 3341},
        {"id": 2, "name": "Дмитрий","surname": "Петров",   "group": 3341},
        {"id": 3, "name": "Алексей","surname": "Сидоров",  "group": 3342},
        {"id": 4, "name": "Мария",   "surname": "Кузнецова","group": 3342},
        {"id": 5, "name": "Кирилл", "surname": "Смирнов",  "group": 3343},
        {"id": 6, "name": "Анна",   "surname": "Новикова", "group": 3343},
        {"id": 7, "name": "Павел",  "surname": "Крючков",  "group": 3341},
        {"id": 8, "name": "Елена",  "surname": "Морозова", "group": 3342},
    ],
    "reports": [
        {
            "id": 1, "student_id": 1,
            "title": "Разработка CLI для обработки изображений",
            "author": "Иванов И.И.", "group": 3341, "subject": "Программирование",
            "words_count": 1250, "flesh_index": 45, "keyword_density": 3,
            "originality": 100.0, "conclusion": True, "bibliography": True, "introduction": True,
            "status": "Готов", "comment": "",
            "parts": [
                {"id": 1, "type": "введение", "chunks": [
                    make_chunk(SHARED_CHUNKS[0]),
                    make_chunk(SHARED_CHUNKS[1]),
                    make_chunk(SHARED_CHUNKS[2]),
                ]},
                {"id": 2, "type": "основная часть", "chunks": [
                    make_chunk(SHARED_CHUNKS[3]),
                    make_chunk(SHARED_CHUNKS[4]),
                    make_chunk("Реализация выравнивания данных в файле и сохранение стандартных значений BMP-заголовков."),
                    make_chunk("Тестирование программы на различных входных данных показало корректность работы алгоритма."),
                    make_chunk("Программа должна быть удобной в использовании, с чётко определёнными функциями и параметрами."),
                ]},
                {"id": 3, "type": "заключение", "chunks": [
                    make_chunk(COMMON_CONCLUSION[0]),
                    make_chunk(COMMON_CONCLUSION[1]),
                ]},
                {"id": 4, "type": "список литературы", "chunks": [
                    make_chunk("1. Кнут Д. Искусство программирования. Том 1. — М.: Вильямс, 2017."),
                    make_chunk("2. Страуструп Б. Язык программирования C++. — М.: Бином, 2019."),
                ]},
            ],
        },
        {
            "id": 2, "student_id": 2,
            "title": "Алгоритмы сортировки и их сравнительный анализ",
            "author": "Петров Д.С.", "group": 3341, "subject": "Алгоритмы",
            "words_count": 1678, "flesh_index": 34, "keyword_density": 4,
            "originality": 88.0, "conclusion": True, "bibliography": True, "introduction": True,
            "status": "Готов", "comment": "",
            "parts": [
                {"id": 5, "type": "введение", "chunks": [
                    make_chunk("Целью данной лабораторной работы является изучение и реализация основных алгоритмов сортировки."),
                    make_chunk("В ходе работы были реализованы алгоритмы: пузырьковая сортировка, сортировка вставками, быстрая сортировка."),
                    make_chunk("Задача — сравнить производительность алгоритмов на различных наборах данных."),
                ]},
                {"id": 6, "type": "основная часть", "chunks": [
                    make_chunk("Пузырьковая сортировка имеет временную сложность O(n²) в худшем случае."),
                    make_chunk("Быстрая сортировка в среднем работает за O(n log n), что делает её предпочтительной для больших массивов."),
                    make_chunk("Сортировка слиянием гарантирует O(n log n) во всех случаях за счёт дополнительной памяти O(n)."),
                    make_chunk("Тестирование проводилось на массивах размером от 100 до 100 000 элементов."),
                ]},
                {"id": 7, "type": "заключение", "chunks": [
                    make_chunk(COMMON_CONCLUSION[0]),
                    make_chunk("По результатам замеров быстрая сортировка оказалась наиболее эффективной на случайных данных."),
                ]},
                {"id": 8, "type": "список литературы", "chunks": [
                    make_chunk("1. Кормен Т., Лейзерсон Ч. Алгоритмы: построение и анализ. — М.: Вильямс, 2013."),
                ]},
            ],
        },
        {
            "id": 3, "student_id": 3,
            "title": "Работа с реляционными базами данных",
            "author": "Сидоров А.В.", "group": 3342, "subject": "Базы данных",
            "words_count": 1876, "flesh_index": 78, "keyword_density": 5,
            "originality": 99.0, "conclusion": True, "bibliography": True, "introduction": True,
            "status": "Готов", "comment": "",
            "parts": [
                {"id": 9, "type": "введение", "chunks": [
                    make_chunk("Целью данной работы является изучение основ работы с реляционными СУБД на примере PostgreSQL."),
                    make_chunk("Реляционные базы данных широко используются в промышленной разработке благодаря надёжности и гибкости."),
                ]},
                {"id": 10, "type": "основная часть", "chunks": [
                    make_chunk("SQL (Structured Query Language) — стандартный язык запросов для работы с реляционными БД."),
                    make_chunk("Основные операции DML: SELECT, INSERT, UPDATE, DELETE позволяют управлять данными."),
                    make_chunk("Индексы ускоряют поиск данных за счёт создания вспомогательных структур."),
                    make_chunk("Транзакции обеспечивают ACID-свойства: атомарность, согласованность, изолированность, долговечность."),
                ]},
                {"id": 11, "type": "заключение", "chunks": [
                    make_chunk("В результате выполнения работы была спроектирована и реализована база данных интернет-магазина."),
                    make_chunk(COMMON_CONCLUSION[2]),
                ]},
                {"id": 12, "type": "список литературы", "chunks": [
                    make_chunk("1. Грофф Д., Вайнберг П. SQL: полное руководство. — М.: Вильямс, 2015."),
                ]},
            ],
        },
        {
            "id": 4, "student_id": 4,
            "title": "Разработка RESTful веб-сервера на Python",
            "author": "Кузнецова М.А.", "group": 3342, "subject": "Веб-разработка",
            "words_count": 1456, "flesh_index": 88, "keyword_density": 6,
            "originality": 78.0, "conclusion": True, "bibliography": False, "introduction": True,
            "status": "Готов", "comment": "Отсутствует список литературы",
            "parts": [
                {"id": 13, "type": "введение", "chunks": [
                    make_chunk("Целью данной лабораторной работы является разработка RESTful API с использованием фреймворка FastAPI."),
                    make_chunk("REST (Representational State Transfer) — архитектурный стиль взаимодействия компонентов распределённого приложения."),
                ]},
                {"id": 14, "type": "основная часть", "chunks": [
                    make_chunk("FastAPI — современный высокопроизводительный фреймворк для создания API на Python."),
                    make_chunk("Для хранения данных используется PostgreSQL в связке с асинхронным драйвером asyncpg."),
                    make_chunk("Маршруты API описываются с помощью декораторов @app.get, @app.post и других HTTP-методов."),
                ]},
                {"id": 15, "type": "заключение", "chunks": [
                    make_chunk(COMMON_CONCLUSION[0]),
                    make_chunk("Разработанный сервер обрабатывает до 10 000 запросов в секунду на тестовом оборудовании."),
                ]},
            ],
        },
        {
            "id": 5, "student_id": 5,
            "title": "Сетевое программирование: TCP/UDP сокеты",
            "author": "Смирнов К.О.", "group": 3343, "subject": "Сети",
            "words_count": 1400, "flesh_index": 67, "keyword_density": 3,
            "originality": 92.0, "conclusion": True, "bibliography": True, "introduction": True,
            "status": "Готов", "comment": "",
            "parts": [
                {"id": 16, "type": "введение", "chunks": [
                    make_chunk("Цель работы — изучение принципов сетевого программирования с использованием сокетов."),
                    make_chunk("Сокеты — программный интерфейс для сетевого взаимодействия между процессами."),
                ]},
                {"id": 17, "type": "основная часть", "chunks": [
                    make_chunk("Протокол TCP обеспечивает надёжную доставку данных с подтверждением получения."),
                    make_chunk("UDP не гарантирует доставку, но обеспечивает меньшую задержку, что критично для потоковых приложений."),
                    make_chunk("В ходе работы реализован чат-сервер на основе TCP-сокетов с поддержкой нескольких клиентов."),
                ]},
                {"id": 18, "type": "заключение", "chunks": [
                    make_chunk("Реализованный чат корректно обрабатывает подключение и отключение клиентов в режиме реального времени."),
                    make_chunk(COMMON_CONCLUSION[1]),
                ]},
                {"id": 19, "type": "список литературы", "chunks": [
                    make_chunk("1. Таненбаум Э. Компьютерные сети. — СПб.: Питер, 2016."),
                ]},
            ],
        },
        {
            "id": 6, "student_id": 6,
            "title": "CLI-приложение для работы с BMP-файлами",
            "author": "Новикова А.Д.", "group": 3343, "subject": "Программирование",
            "words_count": 1340, "flesh_index": 99, "keyword_density": 4,
            "originality": 14.0, "conclusion": True, "bibliography": True, "introduction": True,
            "status": "Готов", "comment": "Высокий процент заимствований!",
            "parts": [
                {"id": 20, "type": "введение", "chunks": [
                    make_chunk(SHARED_CHUNKS[0]),
                    make_chunk(SHARED_CHUNKS[1]),
                    make_chunk(SHARED_CHUNKS[2]),
                ]},
                {"id": 21, "type": "основная часть", "chunks": [
                    make_chunk(SHARED_CHUNKS[3]),
                    make_chunk(SHARED_CHUNKS[4]),
                    make_chunk("Для обработки BMP-файлов была создана библиотека функций на языке C."),
                    make_chunk("Интерфейс командной строки позволяет указывать входной и выходной файлы, а также параметры обработки."),
                ]},
                {"id": 22, "type": "заключение", "chunks": [
                    make_chunk(COMMON_CONCLUSION[0]),
                    make_chunk(COMMON_CONCLUSION[1]),
                ]},
                {"id": 23, "type": "список литературы", "chunks": [
                    make_chunk("1. Страуструп Б. Язык программирования C++. — М.: Бином, 2019."),
                ]},
            ],
        },
        {
            "id": 7, "student_id": 7,
            "title": "Многопоточное программирование на Java",
            "author": "Крючков П.И.", "group": 3341, "subject": "Программирование",
            "words_count": 1700, "flesh_index": 67, "keyword_density": 5,
            "originality": 95.0, "conclusion": True, "bibliography": True, "introduction": True,
            "status": "Готов", "comment": "",
            "parts": [
                {"id": 24, "type": "введение", "chunks": [
                    make_chunk("Целью работы является изучение механизмов многопоточности в Java."),
                    make_chunk("Многопоточность позволяет выполнять несколько задач одновременно, используя несколько ядер процессора."),
                ]},
                {"id": 25, "type": "основная часть", "chunks": [
                    make_chunk("Класс Thread и интерфейс Runnable — базовые инструменты создания потоков в Java."),
                    make_chunk("Механизм synchronized обеспечивает взаимное исключение при доступе к разделяемым ресурсам."),
                    make_chunk("ExecutorService упрощает управление пулом потоков и выполнение асинхронных задач."),
                    make_chunk("Deadlock — ситуация взаимной блокировки потоков, ожидающих освобождения ресурсов друг друга."),
                ]},
                {"id": 26, "type": "заключение", "chunks": [
                    make_chunk(COMMON_CONCLUSION[0]),
                    make_chunk("Реализованный многопоточный сервер демонстрирует прирост производительности до 4x на многоядерном процессоре."),
                ]},
                {"id": 27, "type": "список литературы", "chunks": [
                    make_chunk("1. Блох Д. Java. Эффективное программирование. — М.: Вильямс, 2019."),
                ]},
            ],
        },
        {
            "id": 8, "student_id": 8,
            "title": "Паттерны проектирования: Gang of Four",
            "author": "Морозова Е.С.", "group": 3342, "subject": "ООП",
            "words_count": 1580, "flesh_index": 55, "keyword_density": 4,
            "originality": 91.0, "conclusion": True, "bibliography": True, "introduction": True,
            "status": "Готов", "comment": "",
            "parts": [
                {"id": 28, "type": "введение", "chunks": [
                    make_chunk("Паттерны проектирования — типовые решения часто встречающихся задач в разработке ПО."),
                    make_chunk("Книга «Банды четырёх» описывает 23 классических паттерна, разделённых на три категории."),
                ]},
                {"id": 29, "type": "основная часть", "chunks": [
                    make_chunk("Порождающие паттерны: Singleton, Factory, Abstract Factory, Builder, Prototype."),
                    make_chunk("Структурные паттерны: Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy."),
                    make_chunk("Поведенческие паттерны включают Observer, Strategy, Command, Iterator и другие."),
                    make_chunk("Паттерн Observer реализован для системы событий пользовательского интерфейса."),
                ]},
                {"id": 30, "type": "заключение", "chunks": [
                    make_chunk("В ходе работы реализованы и протестированы пять ключевых паттернов проектирования."),
                    make_chunk(COMMON_CONCLUSION[2]),
                ]},
                {"id": 31, "type": "список литературы", "chunks": [
                    make_chunk("1. Гамма Э. и др. Паттерны объектно-ориентированного проектирования. — СПб.: Питер, 2015."),
                ]},
            ],
        },
    ],
}


def _get_next_chunk_id(current_id: int) -> int:
    return current_id


def seed_data():
    existing = run_query("MATCH (s:Student) RETURN count(s) AS cnt")
    if existing and existing[0]["cnt"] > 0:
        logger.info("Database already seeded, skipping.")
        return

    logger.info("Seeding database with test data...")

    for s in SEED_DATA["students"]:
        run_write(
            "MERGE (s:Student {id: $id}) SET s.name=$name, s.surname=$surname, s.group=$group, s.created_at=$ts, s.updated_at=$ts",
            {**s, "ts": int(__import__("time").time()) - (8 - s["id"]) * 86400 * 10},
        )

    chunk_id_counter = 1

    for report in SEED_DATA["reports"]:
        student_id = report["student_id"]
        report_id = report["id"]
        import time as t
        upload_ts = int(t.time()) - (10 - report_id) * 86400 * 3

        run_write(
            """
            MERGE (r:Report {id: $id})
            SET r.title=$title, r.author=$author, r.group=$group,
                r.subject=$subject, r.words_count=$words_count,
                r.flesh_index=$flesh_index, r.keyword_density=$keyword_density,
                r.originality=$originality, r.conclusion=$conclusion,
                r.bibliography=$bibliography, r.introduction=$introduction,
                r.status=$status, r.upload_date=$upload_date, r.updated_at=$upload_date, r.comment=$comment, r.file_size=null
            """,
            {
                "id": report_id,
                "title": report["title"],
                "author": report["author"],
                "group": report["group"],
                "subject": report["subject"],
                "words_count": report["words_count"],
                "flesh_index": report["flesh_index"],
                "keyword_density": report["keyword_density"],
                "originality": report["originality"],
                "conclusion": report["conclusion"],
                "bibliography": report["bibliography"],
                "introduction": report["introduction"],
                "status": report["status"],
                "upload_date": upload_ts,
                "comment": report.get("comment", ""),
            },
        )

        run_write(
            "MATCH (s:Student {id:$sid}), (r:Report {id:$rid}) MERGE (s)-[:SUBMITTED]->(r)",
            {"sid": student_id, "rid": report_id},
        )

        for part in report["parts"]:
            part_id = part["id"]
            run_write(
                "MERGE (p:Part {id:$id}) SET p.type=$type",
                {"id": part_id, "type": part["type"]},
            )
            run_write(
                "MATCH (r:Report {id:$rid}), (p:Part {id:$pid}) MERGE (r)-[:HAS_PART]->(p)",
                {"rid": report_id, "pid": part_id},
            )

            for chunk in part["chunks"]:
                existing_chunk = run_query(
                    "MATCH (c:Chunk {hash:$hash}) RETURN c.id AS id LIMIT 1",
                    {"hash": chunk["hash"]},
                )
                if existing_chunk:
                    cid = existing_chunk[0]["id"]
                else:
                    cid = chunk_id_counter
                    chunk_id_counter += 1
                    run_write(
                        "MERGE (c:Chunk {id:$id}) SET c.text=$text, c.hash=$hash",
                        {"id": cid, "text": chunk["text"], "hash": chunk["hash"]},
                    )

                run_write(
                    "MATCH (p:Part {id:$pid}), (c:Chunk {id:$cid}) MERGE (p)-[:CONTAINS]->(c)",
                    {"pid": part_id, "cid": cid},
                )

    for report in SEED_DATA["reports"]:
        run_write(
            """
            MATCH (r:Report {id:$rid})-[:HAS_PART]->(:Part)-[:CONTAINS]->(c:Chunk)
            WITH r, c, count{ (c)<-[:CONTAINS]-(:Part)<-[:HAS_PART]-(:Report) } AS usage_count
            WITH r, count(c) AS total_chunks,
                 sum(CASE WHEN usage_count = 1 THEN 1 ELSE 0 END) AS unique_chunks
            SET r.originality = CASE WHEN total_chunks > 0
                THEN round((toFloat(unique_chunks) / total_chunks) * 100.0, 1)
                ELSE 100.0 END
            """,
            {"rid": report["id"]},
        )

    logger.info("Seeding complete.")
