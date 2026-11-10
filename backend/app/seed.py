"""
Demo school data, so every view (Student / Faculty / Management) has
something meaningful to show the moment the app is deployed.

Runs on startup when SEED_DEMO=true and the demo management account does
not exist yet. Also runnable by hand:   python -m app.seed

Demo logins (password for all: Demo@1234)
    management : admin@demo.edu
    faculty    : lakshmi@demo.edu   (Data Structures)
                 suresh@demo.edu    (DBMS + Cloud Computing elective)
                 anjali@demo.edu    (Machine Learning elective)
    student    : student@demo.edu   (or roll number 22AD001)

It also creates 17 more students across two classes with 3 weeks of
realistic activity: pre-assessments, post-preparation tests, consecutive
attempts, sessions and points.
"""
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.core.security import hash_password
from app.services.gamification import POINT_RULES

DEMO_PASSWORD = "Demo@1234"
ADMIN_EMAIL = "admin@demo.edu"

FACULTY = [
    ("lakshmi@demo.edu", "Dr. Lakshmi Prasad"),
    ("suresh@demo.edu", "Prof. Suresh Kumar"),
    ("anjali@demo.edu", "Dr. Anjali Menon"),
]

# code, name, elective, faculty email, {topic: notes}
SUBJECTS = [
    ("CS201", "Data Structures", False, "lakshmi@demo.edu", {
        "Arrays and Strings": "An array stores elements in contiguous memory, so reading index i is O(1) while inserting "
            "in the middle is O(n) because later elements must shift. Strings are arrays of characters. The two-pointer "
            "technique walks two indices toward each other to solve problems such as reversing a string or finding a pair "
            "with a given sum in a sorted array in O(n).",
        "Linked Lists": "A linked list is a chain of nodes where each node holds data and a pointer to the next node. "
            "Insertion and deletion at a known node are O(1), but access by position is O(n). Doubly linked lists also "
            "keep a pointer to the previous node. Reversing a singly linked list uses three pointers: prev, current and next.",
        "Stacks and Queues": "A stack is LIFO (last in, first out) with push and pop at the top; it powers function calls, "
            "undo, and balanced-parenthesis checking. A queue is FIFO (first in, first out) with enqueue at the rear and "
            "dequeue at the front; it is used in scheduling and breadth-first search. Both give O(1) core operations.",
        "Trees and BST": "A binary tree node has at most two children. In a binary search tree every key in the left subtree "
            "is smaller and every key in the right subtree is larger, so search, insert and delete take O(h) where h is the "
            "height. Inorder traversal of a BST visits keys in sorted order; preorder and postorder are used for copying "
            "and deleting trees.",
        "Graphs, BFS and DFS": "A graph is a set of vertices connected by edges, stored as an adjacency list (good for sparse "
            "graphs) or an adjacency matrix (O(1) edge lookup). Breadth-first search uses a queue and finds shortest paths "
            "in unweighted graphs; depth-first search uses recursion or a stack and is used for cycle detection and "
            "topological sorting.",
    }),
    ("CS202", "Database Management Systems", False, "suresh@demo.edu", {
        "ER Modeling": "An entity-relationship model describes entities (things such as Student or Course), their attributes, "
            "and relationships between them with cardinalities like one-to-many or many-to-many. Weak entities depend on "
            "an owner entity for identification. ER diagrams are converted to tables before implementation.",
        "Relational Algebra": "Relational algebra is the formal query language behind SQL. Selection (sigma) filters rows, "
            "projection (pi) picks columns, union, difference and Cartesian product combine relations, and join combines "
            "related tuples from two relations on a condition.",
        "SQL Joins and Aggregation": "SQL INNER JOIN returns rows that match in both tables, LEFT JOIN keeps every row from the "
            "left table, and GROUP BY with aggregate functions such as COUNT, SUM and AVG summarises groups. HAVING filters "
            "groups after aggregation, while WHERE filters rows before it.",
        "Normalization": "Normalization removes redundancy and update anomalies. 1NF requires atomic values, 2NF removes "
            "partial dependencies on part of a composite key, 3NF removes transitive dependencies, and BCNF requires every "
            "determinant to be a candidate key.",
        "Transactions and Concurrency": "A transaction is a unit of work that must satisfy ACID: atomicity, consistency, "
            "isolation and durability. Concurrent transactions can cause lost updates or dirty reads; two-phase locking "
            "and timestamp ordering guarantee serializable schedules.",
    }),
    ("AI301", "Machine Learning", True, "anjali@demo.edu", {
        "Linear Regression": "Linear regression fits y = w x + b by minimising mean squared error. The weights can be found "
            "with the normal equation or with gradient descent, which repeatedly moves the weights against the gradient "
            "scaled by a learning rate.",
        "Logistic Regression": "Logistic regression is a classifier that passes a linear score through the sigmoid function "
            "to output a probability between 0 and 1. It is trained by minimising cross-entropy (log loss), and a threshold "
            "such as 0.5 turns probabilities into class labels.",
        "Decision Trees": "A decision tree splits data on the feature that most reduces impurity, measured by Gini index or "
            "entropy (information gain). Deep trees overfit, so depth limits, minimum samples per leaf, or pruning are used. "
            "Random forests average many trees to reduce variance.",
        "Model Evaluation": "Data is split into training and test sets, or evaluated with k-fold cross-validation. Accuracy can "
            "mislead on imbalanced classes, so precision, recall, F1 score and the confusion matrix are used. Overfitting "
            "shows as high training accuracy but low test accuracy.",
        "K-Means Clustering": "K-means is an unsupervised algorithm that assigns each point to the nearest of k centroids, then "
            "moves each centroid to the mean of its points, repeating until assignments stop changing. The elbow method "
            "helps choose k.",
    }),
    ("CS305", "Cloud Computing", True, "suresh@demo.edu", {
        "Cloud Service Models": "IaaS provides virtual machines, storage and networks (for example AWS EC2); PaaS provides a "
            "managed platform to deploy code without managing servers; SaaS delivers complete applications over the "
            "internet. Deployment models are public, private, hybrid and community clouds.",
        "Virtualization": "A hypervisor lets several virtual machines share one physical server. Type 1 hypervisors run on bare "
            "metal, type 2 run on a host operating system. Virtualization improves utilisation, isolation and lets VMs be "
            "migrated between hosts.",
        "Containers and Docker": "Containers package an application with its dependencies and share the host kernel, so they "
            "start in seconds and use less memory than VMs. A Dockerfile describes an image; images run as containers; "
            "Kubernetes orchestrates containers across a cluster.",
        "Load Balancing and Auto-scaling": "A load balancer spreads incoming requests across healthy servers using algorithms such "
            "as round robin or least connections. Auto-scaling adds or removes instances based on metrics like CPU use, so "
            "capacity follows demand and cost stays low.",
    }),
]

FIRST = ["Ananya", "Karthik", "Meera", "Rahul", "Divya", "Arjun", "Sneha", "Vikram", "Pooja", "Rohit",
         "Kavya", "Nikhil", "Harini", "Sai", "Lavanya", "Aditya", "Bhavana", "Manoj"]
LAST = ["Rao", "Reddy", "Nair", "Sharma", "Iyer", "Varma", "Kumar", "Patel", "Menon", "Gupta",
        "Krishnan", "Joshi", "Pillai", "Naidu", "Chowdary", "Desai", "Bhat", "Shetty"]


def _q5():
    return [{"question": f"Practice question {i + 1}", "options": ["A", "B", "C", "D"], "correct_index": 0}
            for i in range(5)]


def seed_demo(db: Session, embed_fn) -> bool:
    if db.query(models.User).filter(models.User.email == ADMIN_EMAIL).first():
        return False
    rng = random.Random(2026)
    now = datetime.utcnow()
    pw = hash_password(DEMO_PASSWORD)

    db.add(models.User(email=ADMIN_EMAIL, hashed_password=pw, role=models.RoleEnum.management,
                       full_name="Principal (Demo)"))
    faculty = {}
    for email, name in FACULTY:
        f = models.User(email=email, hashed_password=pw, role=models.RoleEnum.instructor, full_name=name)
        db.add(f)
        faculty[email] = f
    db.flush()

    # ---- subjects + content (topics and RAG chunks) ----
    subjects, topics_by_subject = {}, {}
    from app.rag.vector_store import add_chunks

    for code, name, elective, fac_email, notes in SUBJECTS:
        s = models.Subject(code=code, name=name, is_elective=elective, faculty_id=faculty[fac_email].id)
        db.add(s)
        db.flush()
        subjects[code] = s
        doc = models.Document(user_id=faculty[fac_email].id, subject_id=s.id,
                              filename=f"{code}_syllabus_notes.txt", status="ready",
                              uploaded_at=now - timedelta(days=24))
        db.add(doc)
        db.flush()
        topics, chunk_rows = [], []
        for i, (title, text) in enumerate(notes.items()):
            t = models.Topic(document_id=doc.id, title=title, difficulty=["easy", "medium", "hard"][min(i // 2, 2)],
                             order_index=i)
            db.add(t)
            topics.append(t)
            c = models.DocumentChunk(document_id=doc.id, chunk_index=i, content=f"{title}\n\n{text}")
            db.add(c)
            chunk_rows.append(c)
        db.flush()
        topics_by_subject[code] = topics
        try:
            texts = [c.content for c in chunk_rows]
            add_chunks(ids=[c.id for c in chunk_rows], documents=texts, embeddings=embed_fn(texts),
                       metadatas=[{"document_id": doc.id, "user_id": doc.user_id, "chunk_index": c.chunk_index}
                                  for c in chunk_rows])
        except Exception:
            pass  # rebuild_index_if_empty() will retry on next start

    # ---- students ----
    for idx in range(18):
        cls = "CSE-3A" if idx < 9 else "CSE-3B"
        roll = f"22AD{idx + 1:03d}"
        email = "student@demo.edu" if idx == 0 else f"{FIRST[idx].lower()}.{LAST[idx].lower()}@demo.edu"
        st = models.User(email=email, hashed_password=pw, role=models.RoleEnum.student,
                         full_name=f"{FIRST[idx]} {LAST[idx]}", roll_no=roll, class_name=cls,
                         created_at=now - timedelta(days=22))
        db.add(st)
        db.flush()
        elective = "AI301" if idx % 2 == 0 else "CS305"
        enrolled = ["CS201", "CS202", elective]
        for code in enrolled:
            db.add(models.Enrollment(user_id=st.id, subject_id=subjects[code].id))

        ability = rng.uniform(0.35, 0.75) + (0.08 if cls == "CSE-3A" else 0.0)
        diligence = rng.uniform(0.45, 0.95)
        points = []

        # sessions / logins over the last 21 days
        active_days = sorted(rng.sample(range(1, 22), k=max(3, int(21 * diligence * rng.uniform(0.35, 0.7)))))
        if idx == 0:
            active_days = sorted(set(active_days) | {1, 2})       # demo student has a live streak
        for d in active_days:
            start = now - timedelta(days=d, hours=rng.randint(0, 6), minutes=rng.randint(0, 59))
            dur = timedelta(minutes=rng.randint(6, 55))
            db.add(models.UserSession(user_id=st.id, started_at=start, last_seen_at=start + dur))
            db.add(models.ActivityEvent(user_id=st.id, event_type="login", created_at=start))
            points.append((POINT_RULES["daily_login"], "daily_login", "Daily check-in", start))
        if active_days:
            st.last_login_at = now - timedelta(days=active_days[0])

        # score journeys
        for code in enrolled:
            topic_list = topics_by_subject[code]
            # demo student leaves the last two topics of each subject untouched so the
            # pre-assessment -> study kit -> post-test flow can be tried live
            limit = len(topic_list) - 2 if idx == 0 else len(topic_list)
            for ti, topic in enumerate(topic_list[:limit]):
                if rng.random() > diligence - ti * 0.08 and idx != 0:
                    continue
                n_attempts = rng.choice([1, 2, 2, 3, 3, 4])
                score = min(1.0, max(0.0, ability - 0.15 + rng.uniform(-0.15, 0.1) - 0.04 * ti))
                when = now - timedelta(days=rng.randint(4 + ti, 20 + ti), hours=rng.randint(0, 20))
                prev, mastery = None, None
                for a in range(n_attempts):
                    if a > 0:
                        score = min(1.0, score + rng.uniform(0.05, 0.28) * (1.2 if diligence > 0.7 else 1.0))
                        when = min(now - timedelta(hours=2), when + timedelta(days=rng.randint(1, 4)))
                    graded = round(score * 5) / 5
                    kind = ["pre_assessment", "post_preparation"][a] if a < 2 else "practice"
                    db.add(models.QuizAttempt(user_id=st.id, topic_id=topic.id, kind=kind, questions=_q5(),
                                              answers=[0] * 5, score=graded, explanations=[],
                                              created_at=when, submitted_at=when))
                    db.add(models.ActivityEvent(user_id=st.id, event_type="quiz_submitted", created_at=when,
                                                detail={"topic_id": topic.id, "kind": kind, "score": graded}))
                    if a == 0:
                        points.append((POINT_RULES["pre_assessment"], "pre_assessment",
                                       f"Self-assessment: {topic.title}", when))
                        sk = when + timedelta(hours=1)
                        db.add(models.ActivityEvent(user_id=st.id, event_type="study_kit_opened", created_at=sk,
                                                    detail={"topic_id": topic.id, "topic": topic.title}))
                        points.append((POINT_RULES["study_kit_opened"], "study_kit_opened",
                                       f"Started studying {topic.title}", sk))
                    else:
                        points.append((POINT_RULES["quiz_completed"], "quiz_completed",
                                       f"Quiz completed: {topic.title}", when))
                    if prev is not None and graded > prev:
                        gained = round((graded - prev) * 100)
                        points.append((min(POINT_RULES["improvement_cap"], gained), "improvement",
                                       f"Improved {gained}% on {topic.title}", when))
                    was_mastered = mastery is not None and mastery >= 0.75
                    mastery = graded if mastery is None else 0.5 * graded + 0.5 * mastery
                    if not was_mastered and mastery >= 0.75:
                        points.append((POINT_RULES["topic_mastered"], "topic_mastered", f"Mastered {topic.title}", when))
                    prev = graded
                db.add(models.MasteryScore(user_id=st.id, topic_id=topic.id, score=mastery, attempts=n_attempts,
                                           updated_at=when))

        for p, reason, desc, at in points:
            db.add(models.PointsTransaction(user_id=st.id, points=p, reason=reason, description=desc, created_at=at))

    db.commit()

    # study plans for every student
    from app.agent.study_planner import generate_study_plan
    for st in db.query(models.User).filter(models.User.role == models.RoleEnum.student):
        generate_study_plan(db, st.id)
    return True


if __name__ == "__main__":
    from app.database import Base, SessionLocal, engine
    from app.llm.local_embeddings import embed_texts
    from app.migrations import upgrade_schema

    Base.metadata.create_all(bind=engine)
    upgrade_schema(engine)
    session = SessionLocal()
    try:
        created = seed_demo(session, embed_texts)
        print("Demo data created." if created else "Demo data already present — nothing to do.")
    finally:
        session.close()
