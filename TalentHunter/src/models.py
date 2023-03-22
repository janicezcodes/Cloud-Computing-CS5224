from sqlalchemy import create_engine
from sqlalchemy.sql import text
import os

class Models:
    def __init__(self):
        self.engine = create_engine(os.environ.get('DB_URL', 'postgresql://Kaylana:1234@localhost:5432/LibrarySys'))

    def executeRawSql(self, statement, params={}):
        out = None
        with self.engine.connect() as con:
            out = con.execute(text(statement), params)
        return out

    # def addLibrarian(self, value):
    #     return self.executeRawSql("""INSERT INTO Librarian(staff_code, email, password) VALUES(:staff_code, :email, :password);""", value)
    
    def addCandidate(self, value):
        return self.executeRawSql("""INSERT INTO Candidate(candidate_id, name, email, password) VALUES(:candidate_id, :name, :email, :password);""", value)
    
    def addJob(self, value):
        return self.executeRawSql("""INSERT INTO Job(job_id, title, post_date, job_type, description, responsibilities, quelifications) VALUES(:job_id, :title, :post_date, :job_type, :description, :responsibilities, :quelifications);""", value)
    

    def getCandidateByEmail(self, email):
        values = self.executeRawSql("""SELECT * FROM Candidate WHERE email=:email;""", {"email": email}).mappings().all()
        if len(values) == 0:
            raise Exception("User {} does not exist".format(email))
        return values[0]
    

    def getMatches(self):
        return self.executeRawSql("""SELECT * FROM Match LEFT JOIN Book ON Candidate.candidate_id = Match.candidate_id ORDER BY score DESC;""").mappings().all()




    def createModels(self):
        self.executeRawSql(
            """CREATE TABLE IF NOT EXISTS Candidate ( 
                candidate_id VARCHAR(9) PRIMARY KEY, 
                name VARCHAR(64) NOT NULL, 
                email VARCHAR(64) UNIQUE NOT NULL, 
                password VARCHAR(20) NOT NULL
            ); 
            """)
        
        self.executeRawSql(
            """CREATE TABLE IF NOT EXISTS Job (
                job_id VARCHAR(9) PRIMARY KEY, 
                title VARCHAR(64) NOT NULL, 
                post_date DATE NOT NULL,
                job_type VARCHAR(9) NOT NULL,
                description TEXT NOT NULL,
                responsibilities TEXT NOT NULL,
                qualifications TEXT NOT NULL
            );
            """)

        self.executeRawSql( 
            """CREATE TABLE IF NOT EXISTS Match ( 
                candidate_id VARCHAR(9) REFERENCES Candidate(candidate_id) 
                    ON UPDATE CASCADE ON DELETE CASCADE 
                    DEFERRABLE INITIALLY DEFERRED,
                job_id VARCHAR(9) REFERENCES Job(job_id) 
                    ON UPDATE CASCADE ON DELETE CASCADE 
                    DEFERRABLE INITIALLY DEFERRED, 
                score NUMERIC NOT NULL, 
                PRIMARY KEY(candidate_id, job_id)
             ); 
             """)
