from db.core import connect_db

#to use every time when a db session is to be created
#added to seperate db session creation from UI
class DBSession:
    def __enter__(self):
        self.conn = connect_db()
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()

def db_session():
    return DBSession()
