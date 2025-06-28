# init_learning_db.py
"""
Run this script to initialize or reset the learning database schema.
"""

from learning_database.learning_data_locker import LearningDataLocker

def initialize_learning_db():
    locker = LearningDataLocker.get_instance()
    locker.initialize_database()
    print("✅ Learning database schema initialized successfully!")

if __name__ == "__main__":
    initialize_learning_db()
