"""Script to set up the benchmark: creates the Spider 100-question subset SQLite databases and questions.json."""

import json
import sqlite3
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent.parent / "data" / "benchmark_100"
DATABASES_DIR = BENCHMARK_DIR / "databases"
DATABASES_DIR.mkdir(parents=True, exist_ok=True)


# ─── Database Schemas and Sample Data ─────────────────────────────────────────

DATABASES = {
    "concert_singer": {
        "schema_sql": """
CREATE TABLE IF NOT EXISTS stadium (
    Stadium_ID INTEGER PRIMARY KEY,
    Location TEXT,
    Name TEXT,
    Capacity INTEGER,
    Highest INTEGER,
    Lowest INTEGER,
    Average INTEGER
);
CREATE TABLE IF NOT EXISTS singer (
    Singer_ID INTEGER PRIMARY KEY,
    Name TEXT,
    Country TEXT,
    Song_Name TEXT,
    Song_release_year TEXT,
    Age INTEGER,
    Is_male INTEGER
);
CREATE TABLE IF NOT EXISTS concert (
    concert_ID INTEGER PRIMARY KEY,
    concert_Name TEXT,
    Theme TEXT,
    Stadium_ID INTEGER,
    Year TEXT,
    FOREIGN KEY (Stadium_ID) REFERENCES stadium(Stadium_ID)
);
CREATE TABLE IF NOT EXISTS singer_in_concert (
    concert_ID INTEGER,
    Singer_ID INTEGER,
    PRIMARY KEY (concert_ID, Singer_ID),
    FOREIGN KEY (concert_ID) REFERENCES concert(concert_ID),
    FOREIGN KEY (Singer_ID) REFERENCES singer(Singer_ID)
);
""",
        "data_sql": """
INSERT OR IGNORE INTO stadium VALUES (1,'Raith Rovers','Starks Park',10104,4812,1294,2106);
INSERT OR IGNORE INTO stadium VALUES (2,'Ayr United','Somerset Park',11998,2363,1057,1477);
INSERT OR IGNORE INTO stadium VALUES (3,'East Fife','Bayview Stadium',2000,1980,533,864);
INSERT OR IGNORE INTO stadium VALUES (4,'Dumbarton','Strathclyde Homes Stadium',10220,1151,491,774);
INSERT OR IGNORE INTO stadium VALUES (5,'Stirling Albion','Forthbank Stadium',3808,1615,331,765);
INSERT OR IGNORE INTO stadium VALUES (6,'Arbroath','Gayfield Park',4125,921,251,642);
INSERT OR IGNORE INTO stadium VALUES (7,'Alloa Athletic','Recreation Park',3100,1057,331,618);
INSERT OR IGNORE INTO stadium VALUES (8,'Peterhead','Balmoor',3500,980,250,500);
INSERT OR IGNORE INTO singer VALUES (1,'Joe Sharp','Netherlands','You','1992',52,1);
INSERT OR IGNORE INTO singer VALUES (2,'Timbaland','United States','Apologize','2006',32,1);
INSERT OR IGNORE INTO singer VALUES (3,'Taylor Swift','United States','Love Story','2008',22,0);
INSERT OR IGNORE INTO singer VALUES (4,'John Legend','United States','All of Me','2013',34,1);
INSERT OR IGNORE INTO singer VALUES (5,'Katy Perry','United States','Firework','2010',31,0);
INSERT OR IGNORE INTO singer VALUES (6,'Enrique Iglesias','Spain','Hero','2001',45,1);
INSERT OR IGNORE INTO concert VALUES (1,'Auditions','Free choice',1,'2014');
INSERT OR IGNORE INTO concert VALUES (2,'Super bootcamp','Free choice 2',2,'2014');
INSERT OR IGNORE INTO concert VALUES (3,'Home Visits','Bleeding Love',2,'2015');
INSERT OR IGNORE INTO concert VALUES (4,'Week 1','Risk',7,'2014');
INSERT OR IGNORE INTO concert VALUES (5,'Week 1','Fantastic Night',7,'2015');
INSERT OR IGNORE INTO singer_in_concert VALUES (1,1);
INSERT OR IGNORE INTO singer_in_concert VALUES (1,2);
INSERT OR IGNORE INTO singer_in_concert VALUES (2,3);
INSERT OR IGNORE INTO singer_in_concert VALUES (3,1);
INSERT OR IGNORE INTO singer_in_concert VALUES (4,4);
INSERT OR IGNORE INTO singer_in_concert VALUES (5,5);
""",
    },
    "car_1": {
        "schema_sql": """
CREATE TABLE IF NOT EXISTS continents (
    ContId INTEGER PRIMARY KEY,
    Continent TEXT
);
CREATE TABLE IF NOT EXISTS countries (
    CountryId INTEGER PRIMARY KEY,
    CountryName TEXT,
    Continent INTEGER,
    FOREIGN KEY (Continent) REFERENCES continents(ContId)
);
CREATE TABLE IF NOT EXISTS car_makers (
    Id INTEGER PRIMARY KEY,
    Maker TEXT,
    FullName TEXT,
    Country INTEGER,
    FOREIGN KEY (Country) REFERENCES countries(CountryId)
);
CREATE TABLE IF NOT EXISTS model_list (
    ModelId INTEGER PRIMARY KEY,
    Maker INTEGER,
    Model TEXT,
    FOREIGN KEY (Maker) REFERENCES car_makers(Id)
);
CREATE TABLE IF NOT EXISTS car_names (
    MakeId INTEGER PRIMARY KEY,
    Model INTEGER,
    Make TEXT,
    FOREIGN KEY (Model) REFERENCES model_list(ModelId)
);
CREATE TABLE IF NOT EXISTS cars_data (
    Id INTEGER PRIMARY KEY,
    MPG REAL,
    Cylinders INTEGER,
    Displacement REAL,
    Horsepower REAL,
    Weight REAL,
    Accelerate REAL,
    Year INTEGER,
    FOREIGN KEY (Id) REFERENCES car_names(MakeId)
);
""",
        "data_sql": """
INSERT OR IGNORE INTO continents VALUES (1,'America');
INSERT OR IGNORE INTO continents VALUES (2,'Europe');
INSERT OR IGNORE INTO continents VALUES (3,'Asia');
INSERT OR IGNORE INTO countries VALUES (1,'USA',1);
INSERT OR IGNORE INTO countries VALUES (2,'Germany',2);
INSERT OR IGNORE INTO countries VALUES (3,'Japan',3);
INSERT OR IGNORE INTO countries VALUES (4,'France',2);
INSERT OR IGNORE INTO car_makers VALUES (1,'amc','American Motor Company',1);
INSERT OR IGNORE INTO car_makers VALUES (2,'volkswagen','Volkswagen',2);
INSERT OR IGNORE INTO car_makers VALUES (3,'ford','Ford Motor Company',1);
INSERT OR IGNORE INTO car_makers VALUES (4,'toyota','Toyota',3);
INSERT OR IGNORE INTO car_makers VALUES (5,'bmw','BMW',2);
INSERT OR IGNORE INTO model_list VALUES (1,1,'amc');
INSERT OR IGNORE INTO model_list VALUES (2,2,'volkswagen');
INSERT OR IGNORE INTO model_list VALUES (3,3,'ford');
INSERT OR IGNORE INTO model_list VALUES (4,4,'toyota');
INSERT OR IGNORE INTO model_list VALUES (5,5,'bmw');
INSERT OR IGNORE INTO car_names VALUES (1,1,'amc ambassador dpl');
INSERT OR IGNORE INTO car_names VALUES (2,2,'volkswagen 1131 deluxe sedan');
INSERT OR IGNORE INTO car_names VALUES (3,3,'ford maverick');
INSERT OR IGNORE INTO car_names VALUES (4,4,'toyota corolla');
INSERT OR IGNORE INTO car_names VALUES (5,5,'bmw 2002');
INSERT OR IGNORE INTO cars_data VALUES (1,15.0,8,350.0,165.0,3693.0,11.5,1970);
INSERT OR IGNORE INTO cars_data VALUES (2,27.0,4,97.0,60.0,1834.0,19.0,1971);
INSERT OR IGNORE INTO cars_data VALUES (3,21.0,6,200.0,85.0,2587.0,16.0,1970);
INSERT OR IGNORE INTO cars_data VALUES (4,32.0,4,91.0,53.0,1795.0,17.4,1976);
INSERT OR IGNORE INTO cars_data VALUES (5,26.0,4,121.0,113.0,2234.0,12.5,1970);
""",
    },
    "world_1": {
        "schema_sql": """
CREATE TABLE IF NOT EXISTS country (
    Code TEXT PRIMARY KEY,
    Name TEXT,
    Continent TEXT,
    Region TEXT,
    SurfaceArea REAL,
    Population INTEGER,
    LifeExpectancy REAL,
    GNP REAL,
    GovernmentForm TEXT,
    Capital INTEGER
);
CREATE TABLE IF NOT EXISTS city (
    ID INTEGER PRIMARY KEY,
    Name TEXT,
    CountryCode TEXT,
    District TEXT,
    Population INTEGER,
    FOREIGN KEY (CountryCode) REFERENCES country(Code)
);
CREATE TABLE IF NOT EXISTS countrylanguage (
    CountryCode TEXT,
    Language TEXT,
    IsOfficial TEXT,
    Percentage REAL,
    PRIMARY KEY (CountryCode, Language),
    FOREIGN KEY (CountryCode) REFERENCES country(Code)
);
""",
        "data_sql": """
INSERT OR IGNORE INTO country VALUES ('NLD','Netherlands','Europe','Western Europe',41526.0,15864000,78.3,371362.0,'Constitutional Monarchy',1);
INSERT OR IGNORE INTO country VALUES ('USA','United States','North America','North America',9363520.0,278357000,77.1,8510700.0,'Federal Republic',2);
INSERT OR IGNORE INTO country VALUES ('ESP','Spain','Europe','Southern Europe',505992.0,39441700,78.8,553233.0,'Constitutional Monarchy',3);
INSERT OR IGNORE INTO country VALUES ('DEU','Germany','Europe','Western Europe',357022.0,82164700,77.4,2133367.0,'Federal Republic',4);
INSERT OR IGNORE INTO country VALUES ('JPN','Japan','Asia','Eastern Asia',377829.0,126714000,80.7,3787042.0,'Constitutional Monarchy',5);
INSERT OR IGNORE INTO city VALUES (1,'Amsterdam','NLD','Noord-Holland',731200);
INSERT OR IGNORE INTO city VALUES (2,'Washington','USA','District of Columbia',572059);
INSERT OR IGNORE INTO city VALUES (3,'Madrid','ESP','Madrid',2879052);
INSERT OR IGNORE INTO city VALUES (4,'Berlin','DEU','Berliini',3386667);
INSERT OR IGNORE INTO city VALUES (5,'Tokyo','JPN','Tokyo-to',7980230);
INSERT OR IGNORE INTO countrylanguage VALUES ('NLD','Dutch','T',95.6);
INSERT OR IGNORE INTO countrylanguage VALUES ('USA','English','T',86.2);
INSERT OR IGNORE INTO countrylanguage VALUES ('USA','Spanish','F',7.5);
INSERT OR IGNORE INTO countrylanguage VALUES ('ESP','Spanish','T',74.0);
INSERT OR IGNORE INTO countrylanguage VALUES ('DEU','German','T',91.3);
INSERT OR IGNORE INTO countrylanguage VALUES ('JPN','Japanese','T',99.1);
""",
    },
    "employee_hire_evaluation": {
        "schema_sql": """
CREATE TABLE IF NOT EXISTS employee (
    Employee_ID INTEGER PRIMARY KEY,
    Name TEXT,
    Age INTEGER,
    City TEXT
);
CREATE TABLE IF NOT EXISTS shop (
    Shop_ID INTEGER PRIMARY KEY,
    Name TEXT,
    Location TEXT,
    District TEXT,
    Number_products INTEGER,
    Manager_name TEXT
);
CREATE TABLE IF NOT EXISTS hiring (
    Shop_ID INTEGER,
    Employee_ID INTEGER,
    Start_from TEXT,
    Is_full_time INTEGER,
    PRIMARY KEY (Shop_ID, Employee_ID),
    FOREIGN KEY (Shop_ID) REFERENCES shop(Shop_ID),
    FOREIGN KEY (Employee_ID) REFERENCES employee(Employee_ID)
);
CREATE TABLE IF NOT EXISTS evaluation (
    Employee_ID TEXT,
    Year_awarded TEXT,
    Bonus REAL,
    PRIMARY KEY (Employee_ID, Year_awarded)
);
""",
        "data_sql": """
INSERT OR IGNORE INTO employee VALUES (1,'Alice',30,'New York');
INSERT OR IGNORE INTO employee VALUES (2,'Bob',25,'Los Angeles');
INSERT OR IGNORE INTO employee VALUES (3,'Carol',35,'Chicago');
INSERT OR IGNORE INTO employee VALUES (4,'Dave',28,'Houston');
INSERT OR IGNORE INTO employee VALUES (5,'Eve',40,'Phoenix');
INSERT OR IGNORE INTO shop VALUES (1,'Tech World','New York','Manhattan',500,'Alice');
INSERT OR IGNORE INTO shop VALUES (2,'Gadget Hub','Los Angeles','Hollywood',320,'Bob');
INSERT OR IGNORE INTO shop VALUES (3,'Digital Den','Chicago','Loop',410,'Carol');
INSERT OR IGNORE INTO hiring VALUES (1,1,'2020-01-15',1);
INSERT OR IGNORE INTO hiring VALUES (1,2,'2021-03-10',0);
INSERT OR IGNORE INTO hiring VALUES (2,3,'2019-07-01',1);
INSERT OR IGNORE INTO hiring VALUES (3,4,'2022-11-20',1);
INSERT OR IGNORE INTO evaluation VALUES ('1','2021',5000.0);
INSERT OR IGNORE INTO evaluation VALUES ('1','2022',6000.0);
INSERT OR IGNORE INTO evaluation VALUES ('2','2021',3500.0);
INSERT OR IGNORE INTO evaluation VALUES ('3','2022',7000.0);
""",
    },
    "student_transcripts_tracking": {
        "schema_sql": """
CREATE TABLE IF NOT EXISTS Addresses (
    address_id INTEGER PRIMARY KEY,
    line_1 TEXT,
    line_2 TEXT,
    city TEXT,
    zip_postcode TEXT,
    state_province_county TEXT,
    country TEXT
);
CREATE TABLE IF NOT EXISTS Students (
    student_id INTEGER PRIMARY KEY,
    current_address_id INTEGER,
    first_name TEXT,
    middle_name TEXT,
    last_name TEXT,
    cell_mobile_number TEXT,
    email_address TEXT,
    date_first_registered TEXT,
    date_left TEXT,
    FOREIGN KEY (current_address_id) REFERENCES Addresses(address_id)
);
CREATE TABLE IF NOT EXISTS Courses (
    course_id INTEGER PRIMARY KEY,
    course_name TEXT,
    course_description TEXT,
    other_details TEXT
);
CREATE TABLE IF NOT EXISTS Student_Enrolment (
    student_enrolment_id INTEGER PRIMARY KEY,
    degree_program_id INTEGER,
    semester_id INTEGER,
    student_id INTEGER,
    other_details TEXT,
    FOREIGN KEY (student_id) REFERENCES Students(student_id)
);
CREATE TABLE IF NOT EXISTS Transcripts (
    transcript_id INTEGER PRIMARY KEY,
    transcript_date TEXT,
    other_details TEXT
);
CREATE TABLE IF NOT EXISTS Transcript_Contents (
    student_course_id INTEGER PRIMARY KEY,
    transcript_id INTEGER,
    student_enrolment_id INTEGER,
    FOREIGN KEY (transcript_id) REFERENCES Transcripts(transcript_id)
);
""",
        "data_sql": """
INSERT OR IGNORE INTO Addresses VALUES (1,'123 Main St',NULL,'Springfield','62701','Illinois','USA');
INSERT OR IGNORE INTO Addresses VALUES (2,'456 Oak Ave','Apt 2','Shelbyville','62565','Illinois','USA');
INSERT OR IGNORE INTO Students VALUES (1,1,'John','M','Doe','555-1234','john.doe@example.com','2018-09-01','2022-05-15');
INSERT OR IGNORE INTO Students VALUES (2,2,'Jane',NULL,'Smith','555-5678','jane.smith@example.com','2019-09-01',NULL);
INSERT OR IGNORE INTO Students VALUES (3,1,'Bob','A','Johnson','555-9012','bob.j@example.com','2020-01-15',NULL);
INSERT OR IGNORE INTO Courses VALUES (1,'Mathematics','Calculus and Linear Algebra',NULL);
INSERT OR IGNORE INTO Courses VALUES (2,'Physics','Mechanics and Thermodynamics',NULL);
INSERT OR IGNORE INTO Courses VALUES (3,'Computer Science','Programming and Algorithms',NULL);
INSERT OR IGNORE INTO Student_Enrolment VALUES (1,1,1,1,NULL);
INSERT OR IGNORE INTO Student_Enrolment VALUES (2,1,1,2,NULL);
INSERT OR IGNORE INTO Student_Enrolment VALUES (3,2,2,3,NULL);
INSERT OR IGNORE INTO Transcripts VALUES (1,'2022-05-20',NULL);
INSERT OR IGNORE INTO Transcripts VALUES (2,'2023-05-20',NULL);
INSERT OR IGNORE INTO Transcript_Contents VALUES (1,1,1);
INSERT OR IGNORE INTO Transcript_Contents VALUES (2,2,2);
""",
    },
}

# ─── 100 Questions Covering Exactly 20 Per Database ───────────────────────────

QUESTIONS = [
    # ── Database 1: concert_singer (20 questions: IDs 1-20) ───────────────────
    {"id": 1, "db_id": "concert_singer", "question": "How many singers do we have?", "gold_sql": "SELECT count(*) FROM singer", "difficulty": "easy"},
    {"id": 2, "db_id": "concert_singer", "question": "What are all the names and countries of singers?", "gold_sql": "SELECT Name, Country FROM singer", "difficulty": "easy"},
    {"id": 3, "db_id": "concert_singer", "question": "What is the average age of all singers?", "gold_sql": "SELECT avg(Age) FROM singer", "difficulty": "easy"},
    {"id": 4, "db_id": "concert_singer", "question": "What are the names of all stadiums?", "gold_sql": "SELECT Name FROM stadium", "difficulty": "easy"},
    {"id": 5, "db_id": "concert_singer", "question": "How many stadiums are there?", "gold_sql": "SELECT count(*) FROM stadium", "difficulty": "easy"},
    {"id": 6, "db_id": "concert_singer", "question": "What is the maximum capacity among all stadiums?", "gold_sql": "SELECT max(Capacity) FROM stadium", "difficulty": "easy"},
    {"id": 7, "db_id": "concert_singer", "question": "What is the average and maximum capacity of all stadiums?", "gold_sql": "SELECT avg(Capacity), max(Capacity) FROM stadium", "difficulty": "easy"},
    {"id": 8, "db_id": "concert_singer", "question": "List all singer names in descending order of age.", "gold_sql": "SELECT Name FROM singer ORDER BY Age DESC", "difficulty": "medium"},
    {"id": 9, "db_id": "concert_singer", "question": "What is the name and age of the youngest singer?", "gold_sql": "SELECT Name, Age FROM singer ORDER BY Age ASC LIMIT 1", "difficulty": "medium"},
    {"id": 10, "db_id": "concert_singer", "question": "Show the name and the release year of the song by the youngest singer.", "gold_sql": "SELECT Song_Name, Song_release_year FROM singer ORDER BY Age ASC LIMIT 1", "difficulty": "medium"},
    {"id": 11, "db_id": "concert_singer", "question": "What is the name and capacity of the stadium with the highest capacity?", "gold_sql": "SELECT Name, Capacity FROM stadium ORDER BY Capacity DESC LIMIT 1", "difficulty": "medium"},
    {"id": 12, "db_id": "concert_singer", "question": "Show the stadium name and the number of concerts held in each stadium.", "gold_sql": "SELECT T1.Name, count(*) FROM stadium AS T1 JOIN concert AS T2 ON T1.Stadium_ID = T2.Stadium_ID GROUP BY T1.Name", "difficulty": "medium"},
    {"id": 13, "db_id": "concert_singer", "question": "List the names of singers who have been in more than one concert.", "gold_sql": "SELECT T1.Name FROM singer AS T1 JOIN singer_in_concert AS T2 ON T1.Singer_ID = T2.Singer_ID GROUP BY T1.Name HAVING count(*) > 1", "difficulty": "medium"},
    {"id": 14, "db_id": "concert_singer", "question": "Find the names of concerts and their corresponding stadium names.", "gold_sql": "SELECT T1.concert_Name, T2.Name FROM concert AS T1 JOIN stadium AS T2 ON T1.Stadium_ID = T2.Stadium_ID", "difficulty": "medium"},
    {"id": 15, "db_id": "concert_singer", "question": "Find the name and age of singers whose age is greater than the average age of all singers.", "gold_sql": "SELECT Name, Age FROM singer WHERE Age > (SELECT avg(Age) FROM singer)", "difficulty": "hard"},
    {"id": 16, "db_id": "concert_singer", "question": "Find the names of stadiums that have never held a concert.", "gold_sql": "SELECT Name FROM stadium WHERE Stadium_ID NOT IN (SELECT Stadium_ID FROM concert)", "difficulty": "hard"},
    {"id": 17, "db_id": "concert_singer", "question": "Find singer names who did not participate in any concert.", "gold_sql": "SELECT Name FROM singer WHERE Singer_ID NOT IN (SELECT Singer_ID FROM singer_in_concert)", "difficulty": "hard"},
    {"id": 18, "db_id": "concert_singer", "question": "List the name and capacity of stadiums that have hosted more than one concert.", "gold_sql": "SELECT T1.Name, T1.Capacity FROM stadium AS T1 JOIN concert AS T2 ON T1.Stadium_ID = T2.Stadium_ID GROUP BY T1.Name HAVING count(*) > 1", "difficulty": "hard"},
    {"id": 19, "db_id": "concert_singer", "question": "Find the names of singers who have appeared in both a 2014 and a 2015 concert.", "gold_sql": "SELECT T1.Name FROM singer AS T1 JOIN singer_in_concert AS T2 ON T1.Singer_ID = T2.Singer_ID JOIN concert AS T3 ON T2.concert_ID = T3.concert_ID WHERE T3.Year = '2014' INTERSECT SELECT T1.Name FROM singer AS T1 JOIN singer_in_concert AS T2 ON T1.Singer_ID = T2.Singer_ID JOIN concert AS T3 ON T2.concert_ID = T3.concert_ID WHERE T3.Year = '2015'", "difficulty": "extra-hard"},
    {"id": 20, "db_id": "concert_singer", "question": "Find the country with the most singers.", "gold_sql": "SELECT Country FROM singer GROUP BY Country ORDER BY count(*) DESC LIMIT 1", "difficulty": "extra-hard"},

    # ── Database 2: car_1 (20 questions: IDs 21-40) ───────────────────────────
    {"id": 21, "db_id": "car_1", "question": "How many car makers are there?", "gold_sql": "SELECT count(*) FROM car_makers", "difficulty": "easy"},
    {"id": 22, "db_id": "car_1", "question": "List all countries and their continents.", "gold_sql": "SELECT T1.CountryName, T2.Continent FROM countries AS T1 JOIN continents AS T2 ON T1.Continent = T2.ContId", "difficulty": "easy"},
    {"id": 23, "db_id": "car_1", "question": "What are the full names of all car makers?", "gold_sql": "SELECT FullName FROM car_makers", "difficulty": "easy"},
    {"id": 24, "db_id": "car_1", "question": "How many cars were made in 1970?", "gold_sql": "SELECT count(*) FROM cars_data WHERE Year = 1970", "difficulty": "easy"},
    {"id": 25, "db_id": "car_1", "question": "What is the average MPG of all cars?", "gold_sql": "SELECT avg(MPG) FROM cars_data", "difficulty": "easy"},
    {"id": 26, "db_id": "car_1", "question": "What is the maximum and minimum horsepower of all cars?", "gold_sql": "SELECT max(Horsepower), min(Horsepower) FROM cars_data", "difficulty": "easy"},
    {"id": 27, "db_id": "car_1", "question": "What are the car makes and their models?", "gold_sql": "SELECT T1.Make, T2.Model FROM car_names AS T1 JOIN model_list AS T2 ON T1.Model = T2.ModelId", "difficulty": "easy"},
    {"id": 28, "db_id": "car_1", "question": "What is the number of car models made by each car maker?", "gold_sql": "SELECT T1.FullName, count(T2.ModelId) FROM car_makers AS T1 JOIN model_list AS T2 ON T1.Id = T2.Maker GROUP BY T1.FullName", "difficulty": "medium"},
    {"id": 29, "db_id": "car_1", "question": "List the car make and year for all cars with more than 6 cylinders.", "gold_sql": "SELECT T1.Make, T2.Year FROM car_names AS T1 JOIN cars_data AS T2 ON T1.MakeId = T2.Id WHERE T2.Cylinders > 6", "difficulty": "medium"},
    {"id": 30, "db_id": "car_1", "question": "Find the car with the highest MPG and return its make.", "gold_sql": "SELECT T1.Make FROM car_names AS T1 JOIN cars_data AS T2 ON T1.MakeId = T2.Id ORDER BY T2.MPG DESC LIMIT 1", "difficulty": "medium"},
    {"id": 31, "db_id": "car_1", "question": "How many car makers are there in each continent?", "gold_sql": "SELECT T3.Continent, count(*) FROM car_makers AS T1 JOIN countries AS T2 ON T1.Country = T2.CountryId JOIN continents AS T3 ON T2.Continent = T3.ContId GROUP BY T3.Continent", "difficulty": "medium"},
    {"id": 32, "db_id": "car_1", "question": "What is the average weight of cars made in 1970?", "gold_sql": "SELECT avg(Weight) FROM cars_data WHERE Year = 1970", "difficulty": "medium"},
    {"id": 33, "db_id": "car_1", "question": "What is the average horsepower of cars made in 1970?", "gold_sql": "SELECT avg(Horsepower) FROM cars_data WHERE Year = 1970", "difficulty": "medium"},
    {"id": 34, "db_id": "car_1", "question": "What is the average MPG of cars made in the USA?", "gold_sql": "SELECT avg(T1.MPG) FROM cars_data AS T1 JOIN car_names AS T2 ON T1.Id = T2.MakeId JOIN model_list AS T3 ON T2.Model = T3.ModelId JOIN car_makers AS T4 ON T3.Maker = T4.Id JOIN countries AS T5 ON T4.Country = T5.CountryId WHERE T5.CountryName = 'USA'", "difficulty": "medium"},
    {"id": 35, "db_id": "car_1", "question": "Which countries have more than 1 car maker?", "gold_sql": "SELECT T2.CountryName FROM car_makers AS T1 JOIN countries AS T2 ON T1.Country = T2.CountryId GROUP BY T2.CountryName HAVING count(*) > 1", "difficulty": "hard"},
    {"id": 36, "db_id": "car_1", "question": "What are the makers and models of cars with an MPG greater than the average MPG?", "gold_sql": "SELECT T2.FullName, T3.Model FROM cars_data AS T1 JOIN car_names AS T4 ON T1.Id = T4.MakeId JOIN model_list AS T3 ON T4.Model = T3.ModelId JOIN car_makers AS T2 ON T3.Maker = T2.Id WHERE T1.MPG > (SELECT avg(MPG) FROM cars_data)", "difficulty": "hard"},
    {"id": 37, "db_id": "car_1", "question": "Find the average horsepower of cars grouped by number of cylinders, only for cylinder counts with average horsepower above 100.", "gold_sql": "SELECT Cylinders, avg(Horsepower) FROM cars_data GROUP BY Cylinders HAVING avg(Horsepower) > 100", "difficulty": "hard"},
    {"id": 38, "db_id": "car_1", "question": "Find car makers that do not have any cars in cars_data.", "gold_sql": "SELECT FullName FROM car_makers WHERE Id NOT IN (SELECT T1.Maker FROM model_list AS T1 JOIN car_names AS T2 ON T1.ModelId = T2.Model JOIN cars_data AS T3 ON T2.MakeId = T3.Id)", "difficulty": "hard"},
    {"id": 39, "db_id": "car_1", "question": "Find the country that has the maker with the most models.", "gold_sql": "SELECT T2.CountryName FROM car_makers AS T1 JOIN countries AS T2 ON T1.Country = T2.CountryId JOIN model_list AS T3 ON T1.Id = T3.Maker GROUP BY T2.CountryName ORDER BY count(*) DESC LIMIT 1", "difficulty": "extra-hard"},
    {"id": 40, "db_id": "car_1", "question": "Find car makers that have models with 4 cylinders and also models with 8 cylinders.", "gold_sql": "SELECT T3.FullName FROM cars_data AS T1 JOIN model_list AS T2 ON T1.Id = T2.ModelId JOIN car_makers AS T3 ON T2.Maker = T3.Id WHERE T1.Cylinders = 4 INTERSECT SELECT T3.FullName FROM cars_data AS T1 JOIN model_list AS T2 ON T1.Id = T2.ModelId JOIN car_makers AS T3 ON T2.Maker = T3.Id WHERE T1.Cylinders = 8", "difficulty": "extra-hard"},

    # ── Database 3: world_1 (20 questions: IDs 41-60) ─────────────────────────
    {"id": 41, "db_id": "world_1", "question": "How many countries are in Europe?", "gold_sql": "SELECT count(*) FROM country WHERE Continent = 'Europe'", "difficulty": "easy"},
    {"id": 42, "db_id": "world_1", "question": "What are the names of all countries in Asia?", "gold_sql": "SELECT Name FROM country WHERE Continent = 'Asia'", "difficulty": "easy"},
    {"id": 43, "db_id": "world_1", "question": "What is the total population of all countries?", "gold_sql": "SELECT sum(Population) FROM country", "difficulty": "easy"},
    {"id": 44, "db_id": "world_1", "question": "What is the average life expectancy in Europe?", "gold_sql": "SELECT avg(LifeExpectancy) FROM country WHERE Continent = 'Europe'", "difficulty": "easy"},
    {"id": 45, "db_id": "world_1", "question": "List all cities and their population.", "gold_sql": "SELECT Name, Population FROM city", "difficulty": "easy"},
    {"id": 46, "db_id": "world_1", "question": "What is the name and population of the most populous city?", "gold_sql": "SELECT Name, Population FROM city ORDER BY Population DESC LIMIT 1", "difficulty": "easy"},
    {"id": 47, "db_id": "world_1", "question": "What are the names and populations of countries with a population greater than 100 million?", "gold_sql": "SELECT Name, Population FROM country WHERE Population > 100000000", "difficulty": "medium"},
    {"id": 48, "db_id": "world_1", "question": "List the official languages and the countries that speak them.", "gold_sql": "SELECT T1.Name, T2.Language FROM country AS T1 JOIN countrylanguage AS T2 ON T1.Code = T2.CountryCode WHERE T2.IsOfficial = 'T'", "difficulty": "medium"},
    {"id": 49, "db_id": "world_1", "question": "Find the names of countries and their capital city names.", "gold_sql": "SELECT T1.Name, T2.Name FROM country AS T1 JOIN city AS T2 ON T1.Capital = T2.ID", "difficulty": "medium"},
    {"id": 50, "db_id": "world_1", "question": "What is the number of languages spoken in each country?", "gold_sql": "SELECT CountryCode, count(*) FROM countrylanguage GROUP BY CountryCode", "difficulty": "medium"},
    {"id": 51, "db_id": "world_1", "question": "What continent has the highest total GNP?", "gold_sql": "SELECT Continent FROM country GROUP BY Continent ORDER BY sum(GNP) DESC LIMIT 1", "difficulty": "medium"},
    {"id": 52, "db_id": "world_1", "question": "List all cities in Europe with a population greater than 1 million.", "gold_sql": "SELECT T2.Name FROM country AS T1 JOIN city AS T2 ON T1.Code = T2.CountryCode WHERE T1.Continent = 'Europe' AND T2.Population > 1000000", "difficulty": "medium"},
    {"id": 53, "db_id": "world_1", "question": "What is the average life expectancy for countries grouped by continent?", "gold_sql": "SELECT Continent, avg(LifeExpectancy) FROM country GROUP BY Continent", "difficulty": "medium"},
    {"id": 54, "db_id": "world_1", "question": "Find countries with life expectancy above average.", "gold_sql": "SELECT Name FROM country WHERE LifeExpectancy > (SELECT avg(LifeExpectancy) FROM country)", "difficulty": "medium"},
    {"id": 55, "db_id": "world_1", "question": "List the top 3 most populous countries by continent.", "gold_sql": "SELECT Name, Continent, Population FROM country ORDER BY Population DESC LIMIT 3", "difficulty": "hard"},
    {"id": 56, "db_id": "world_1", "question": "Find countries that have no official language recorded.", "gold_sql": "SELECT Name FROM country WHERE Code NOT IN (SELECT CountryCode FROM countrylanguage WHERE IsOfficial = 'T')", "difficulty": "hard"},
    {"id": 57, "db_id": "world_1", "question": "List country names where the capital city's population is more than 1 million.", "gold_sql": "SELECT T1.Name FROM country AS T1 JOIN city AS T2 ON T1.Capital = T2.ID WHERE T2.Population > 1000000", "difficulty": "hard"},
    {"id": 58, "db_id": "world_1", "question": "Find the total number of cities in countries with a population above 50 million.", "gold_sql": "SELECT count(*) FROM city AS T1 JOIN country AS T2 ON T1.CountryCode = T2.Code WHERE T2.Population > 50000000", "difficulty": "hard"},
    {"id": 59, "db_id": "world_1", "question": "Find countries where English is an official language but French is not.", "gold_sql": "SELECT CountryCode FROM countrylanguage WHERE Language = 'English' AND IsOfficial = 'T' EXCEPT SELECT CountryCode FROM countrylanguage WHERE Language = 'French'", "difficulty": "extra-hard"},
    {"id": 60, "db_id": "world_1", "question": "List the top 3 countries with the highest number of cities.", "gold_sql": "SELECT T1.Name, count(T2.ID) AS city_count FROM country AS T1 JOIN city AS T2 ON T1.Code = T2.CountryCode GROUP BY T1.Name ORDER BY city_count DESC LIMIT 3", "difficulty": "extra-hard"},

    # ── Database 4: employee_hire_evaluation (20 questions: IDs 61-80) ────────
    {"id": 61, "db_id": "employee_hire_evaluation", "question": "How many employees are there?", "gold_sql": "SELECT count(*) FROM employee", "difficulty": "easy"},
    {"id": 62, "db_id": "employee_hire_evaluation", "question": "List all employee names and their ages.", "gold_sql": "SELECT Name, Age FROM employee", "difficulty": "easy"},
    {"id": 63, "db_id": "employee_hire_evaluation", "question": "What is the name and location of each shop?", "gold_sql": "SELECT Name, Location FROM shop", "difficulty": "easy"},
    {"id": 64, "db_id": "employee_hire_evaluation", "question": "What is the average age of all employees?", "gold_sql": "SELECT avg(Age) FROM employee", "difficulty": "easy"},
    {"id": 65, "db_id": "employee_hire_evaluation", "question": "What is the total bonus given to employee with ID 1?", "gold_sql": "SELECT sum(Bonus) FROM evaluation WHERE Employee_ID = '1'", "difficulty": "easy"},
    {"id": 66, "db_id": "employee_hire_evaluation", "question": "List shops with more than 400 products.", "gold_sql": "SELECT Name FROM shop WHERE Number_products > 400", "difficulty": "easy"},
    {"id": 67, "db_id": "employee_hire_evaluation", "question": "What is the name of the manager of the shop in New York?", "gold_sql": "SELECT Manager_name FROM shop WHERE Location = 'New York'", "difficulty": "easy"},
    {"id": 68, "db_id": "employee_hire_evaluation", "question": "List the names of full-time employees.", "gold_sql": "SELECT T1.Name FROM employee AS T1 JOIN hiring AS T2 ON T1.Employee_ID = T2.Employee_ID WHERE T2.Is_full_time = 1", "difficulty": "medium"},
    {"id": 69, "db_id": "employee_hire_evaluation", "question": "What shops and how many employees does each one have?", "gold_sql": "SELECT T1.Name, count(T2.Employee_ID) FROM shop AS T1 JOIN hiring AS T2 ON T1.Shop_ID = T2.Shop_ID GROUP BY T1.Name", "difficulty": "medium"},
    {"id": 70, "db_id": "employee_hire_evaluation", "question": "Find the total bonus received by each employee.", "gold_sql": "SELECT Employee_ID, sum(Bonus) FROM evaluation GROUP BY Employee_ID", "difficulty": "medium"},
    {"id": 71, "db_id": "employee_hire_evaluation", "question": "List the names and cities of employees who work in a shop in New York.", "gold_sql": "SELECT T1.Name, T1.City FROM employee AS T1 JOIN hiring AS T2 ON T1.Employee_ID = T2.Employee_ID JOIN shop AS T3 ON T2.Shop_ID = T3.Shop_ID WHERE T3.Location = 'New York'", "difficulty": "medium"},
    {"id": 72, "db_id": "employee_hire_evaluation", "question": "What is the average bonus per year for all evaluations?", "gold_sql": "SELECT Year_awarded, avg(Bonus) FROM evaluation GROUP BY Year_awarded", "difficulty": "medium"},
    {"id": 73, "db_id": "employee_hire_evaluation", "question": "Find the name and age of the oldest employee.", "gold_sql": "SELECT Name, Age FROM employee ORDER BY Age DESC LIMIT 1", "difficulty": "medium"},
    {"id": 74, "db_id": "employee_hire_evaluation", "question": "Find the average bonus awarded in 2021.", "gold_sql": "SELECT avg(Bonus) FROM evaluation WHERE Year_awarded = '2021'", "difficulty": "medium"},
    {"id": 75, "db_id": "employee_hire_evaluation", "question": "Find employee names who have received a bonus above average.", "gold_sql": "SELECT DISTINCT T1.Name FROM employee AS T1 JOIN evaluation AS T2 ON T1.Employee_ID = CAST(T2.Employee_ID AS INTEGER) WHERE T2.Bonus > (SELECT avg(Bonus) FROM evaluation)", "difficulty": "hard"},
    {"id": 76, "db_id": "employee_hire_evaluation", "question": "Which employees have never been evaluated?", "gold_sql": "SELECT Name FROM employee WHERE Employee_ID NOT IN (SELECT CAST(Employee_ID AS INTEGER) FROM evaluation)", "difficulty": "hard"},
    {"id": 77, "db_id": "employee_hire_evaluation", "question": "What is the total bonus for employees hired before 2021?", "gold_sql": "SELECT sum(T2.Bonus) FROM hiring AS T1 JOIN evaluation AS T2 ON T1.Employee_ID = CAST(T2.Employee_ID AS INTEGER) WHERE T1.Start_from < '2021-01-01'", "difficulty": "hard"},
    {"id": 78, "db_id": "employee_hire_evaluation", "question": "Find the shop with the most employees.", "gold_sql": "SELECT T1.Name FROM shop AS T1 JOIN hiring AS T2 ON T1.Shop_ID = T2.Shop_ID GROUP BY T1.Name ORDER BY count(*) DESC LIMIT 1", "difficulty": "hard"},
    {"id": 79, "db_id": "employee_hire_evaluation", "question": "List shops that have both full-time and part-time employees.", "gold_sql": "SELECT T1.Name FROM shop AS T1 JOIN hiring AS T2 ON T1.Shop_ID = T2.Shop_ID WHERE T2.Is_full_time = 1 INTERSECT SELECT T1.Name FROM shop AS T1 JOIN hiring AS T2 ON T1.Shop_ID = T2.Shop_ID WHERE T2.Is_full_time = 0", "difficulty": "extra-hard"},
    {"id": 80, "db_id": "employee_hire_evaluation", "question": "Find the names of employees who received a bonus in 2021 but not in 2022.", "gold_sql": "SELECT T1.Name FROM employee AS T1 JOIN evaluation AS T2 ON T1.Employee_ID = CAST(T2.Employee_ID AS INTEGER) WHERE T2.Year_awarded = '2021' EXCEPT SELECT T1.Name FROM employee AS T1 JOIN evaluation AS T2 ON T1.Employee_ID = CAST(T2.Employee_ID AS INTEGER) WHERE T2.Year_awarded = '2022'", "difficulty": "extra-hard"},

    # ── Database 5: student_transcripts_tracking (20 questions: IDs 81-100) ───
    {"id": 81, "db_id": "student_transcripts_tracking", "question": "How many students are there?", "gold_sql": "SELECT count(*) FROM Students", "difficulty": "easy"},
    {"id": 82, "db_id": "student_transcripts_tracking", "question": "List all first and last names of students.", "gold_sql": "SELECT first_name, last_name FROM Students", "difficulty": "easy"},
    {"id": 83, "db_id": "student_transcripts_tracking", "question": "How many courses are available?", "gold_sql": "SELECT count(*) FROM Courses", "difficulty": "easy"},
    {"id": 84, "db_id": "student_transcripts_tracking", "question": "List all course names and descriptions.", "gold_sql": "SELECT course_name, course_description FROM Courses", "difficulty": "easy"},
    {"id": 85, "db_id": "student_transcripts_tracking", "question": "What are the email addresses of all students?", "gold_sql": "SELECT email_address FROM Students", "difficulty": "easy"},
    {"id": 86, "db_id": "student_transcripts_tracking", "question": "How many transcripts have been issued?", "gold_sql": "SELECT count(*) FROM Transcripts", "difficulty": "easy"},
    {"id": 87, "db_id": "student_transcripts_tracking", "question": "What cities do students currently live in?", "gold_sql": "SELECT DISTINCT T2.city FROM Students AS T1 JOIN Addresses AS T2 ON T1.current_address_id = T2.address_id", "difficulty": "easy"},
    {"id": 88, "db_id": "student_transcripts_tracking", "question": "How many students are enrolled in each degree program?", "gold_sql": "SELECT degree_program_id, count(*) FROM Student_Enrolment GROUP BY degree_program_id", "difficulty": "medium"},
    {"id": 89, "db_id": "student_transcripts_tracking", "question": "What is the number of student enrolments per semester?", "gold_sql": "SELECT semester_id, count(*) FROM Student_Enrolment GROUP BY semester_id", "difficulty": "medium"},
    {"id": 90, "db_id": "student_transcripts_tracking", "question": "List the first names and email addresses of students who have left.", "gold_sql": "SELECT first_name, email_address FROM Students WHERE date_left IS NOT NULL", "difficulty": "medium"},
    {"id": 91, "db_id": "student_transcripts_tracking", "question": "Find students who registered after 2019.", "gold_sql": "SELECT first_name, last_name FROM Students WHERE date_first_registered > '2019-12-31'", "difficulty": "medium"},
    {"id": 92, "db_id": "student_transcripts_tracking", "question": "List students and their current city.", "gold_sql": "SELECT T1.first_name, T1.last_name, T2.city FROM Students AS T1 JOIN Addresses AS T2 ON T1.current_address_id = T2.address_id", "difficulty": "medium"},
    {"id": 93, "db_id": "student_transcripts_tracking", "question": "How many transcript contents are there for each transcript?", "gold_sql": "SELECT transcript_id, count(*) FROM Transcript_Contents GROUP BY transcript_id", "difficulty": "medium"},
    {"id": 94, "db_id": "student_transcripts_tracking", "question": "Find the number of enrolments for each student.", "gold_sql": "SELECT student_id, count(*) FROM Student_Enrolment GROUP BY student_id", "difficulty": "medium"},
    {"id": 95, "db_id": "student_transcripts_tracking", "question": "Find the first and last names of students who have a transcript.", "gold_sql": "SELECT DISTINCT T1.first_name, T1.last_name FROM Students AS T1 JOIN Student_Enrolment AS T2 ON T1.student_id = T2.student_id JOIN Transcript_Contents AS T3 ON T2.student_enrolment_id = T3.student_enrolment_id", "difficulty": "hard"},
    {"id": 96, "db_id": "student_transcripts_tracking", "question": "What is the number of students who do not have any enrolment?", "gold_sql": "SELECT count(*) FROM Students WHERE student_id NOT IN (SELECT student_id FROM Student_Enrolment)", "difficulty": "hard"},
    {"id": 97, "db_id": "student_transcripts_tracking", "question": "Find the state or province of addresses used by enrolled students.", "gold_sql": "SELECT DISTINCT T3.state_province_county FROM Student_Enrolment AS T1 JOIN Students AS T2 ON T1.student_id = T2.student_id JOIN Addresses AS T3 ON T2.current_address_id = T3.address_id", "difficulty": "hard"},
    {"id": 98, "db_id": "student_transcripts_tracking", "question": "List the number of students per city.", "gold_sql": "SELECT T2.city, count(*) FROM Students AS T1 JOIN Addresses AS T2 ON T1.current_address_id = T2.address_id GROUP BY T2.city", "difficulty": "hard"},
    {"id": 99, "db_id": "student_transcripts_tracking", "question": "Find students who registered in 2018.", "gold_sql": "SELECT first_name, last_name FROM Students WHERE date_first_registered LIKE '2018%'", "difficulty": "extra-hard"},
    {"id": 100, "db_id": "student_transcripts_tracking", "question": "List students who are enrolled in more than one semester.", "gold_sql": "SELECT T1.first_name, T1.last_name FROM Students AS T1 JOIN Student_Enrolment AS T2 ON T1.student_id = T2.student_id GROUP BY T1.student_id HAVING count(DISTINCT T2.semester_id) > 1", "difficulty": "extra-hard"},
]


def build_database(db_id: str, schema_sql: str, data_sql: str) -> Path:
    db_file = DATABASES_DIR / f"{db_id}.sqlite"
    # Remove old file so we start fresh
    if db_file.exists():
        db_file.unlink()
    conn = sqlite3.connect(str(db_file))
    try:
        combined = schema_sql.strip() + "\n" + data_sql.strip()
        conn.executescript(combined)
        conn.commit()
        print(f"  [OK] Built database: {db_id}.sqlite")
    finally:
        conn.close()
    return db_file


def verify_benchmark_questions():
    """Verify that every gold_sql executes successfully against its target SQLite database."""
    print("\nVerifying 100 gold benchmark queries against databases...")
    questions_file = BENCHMARK_DIR / "questions.json"
    with open(questions_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    if len(questions) != 100:
        raise ValueError(f"Expected exactly 100 questions, found {len(questions)}")

    counts = {}
    for q in questions:
        db_id = q["db_id"]
        counts[db_id] = counts.get(db_id, 0) + 1

    for db_id, count in counts.items():
        if count != 20:
            raise ValueError(f"Database '{db_id}' has {count} questions, expected 20.")

    failures = []
    for q in questions:
        db_path = DATABASES_DIR / f"{q['db_id']}.sqlite"
        if not db_path.exists():
            failures.append((q["id"], f"Database not found: {db_path}"))
            continue
        conn = sqlite3.connect(str(db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(q["gold_sql"])
            _ = cursor.fetchall()
        except Exception as e:
            failures.append((q["id"], f"{e} | SQL: {q['gold_sql']}"))
        finally:
            conn.close()

    if failures:
        print(f"\n[ERROR] {len(failures)} gold SQL queries failed validation!")
        for qid, err in failures:
            print(f"  - Question {qid}: {err}")
        raise RuntimeError(f"Benchmark verification failed for {len(failures)} queries.")

    print(f"  [OK] All {len(questions)} gold queries successfully executed against their databases!\n")


def setup_benchmark():
    print(f"Setting up benchmark data at: {BENCHMARK_DIR}")
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    DATABASES_DIR.mkdir(parents=True, exist_ok=True)

    for db_id, db_data in DATABASES.items():
        build_database(db_id, db_data["schema_sql"], db_data["data_sql"])

    questions_file = BENCHMARK_DIR / "questions.json"
    with open(questions_file, "w", encoding="utf-8") as f:
        json.dump(QUESTIONS, f, indent=2, ensure_ascii=False)

    print(f"  [OK] Written {len(QUESTIONS)} questions to questions.json")
    
    # Run mandatory verification
    verify_benchmark_questions()
    
    print("[SUCCESS] Benchmark setup complete!")
    print(f"   Databases: {DATABASES_DIR}")
    print(f"   Questions: {questions_file}")


if __name__ == "__main__":
    setup_benchmark()
