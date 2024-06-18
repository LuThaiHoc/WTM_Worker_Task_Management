from sqlalchemy import create_engine, Column, Integer, Text, Float, Boolean, exc, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import json, os

class DatabaseConfig():
    def __init__(self,host="localhost", database="diary_management", user="postgres", password="123456", port=5432):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        
    def save_to_json(self, file_path='config.json'):
        if not os.path.exists(file_path):
            settings = {}
        else:
            with open(file_path, 'r') as json_file:
                settings = json.load(json_file)

        settings['database'] = {
            'host': self.host,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'port': self.port
        }
        
        with open(file_path, 'w') as json_file:
            json.dump(settings, json_file, indent=4)
        print(f"Database settings saved to {file_path}")

    @classmethod
    def read_from_json(cls, file_path='config.json'):
        if not os.path.exists(file_path):
            print(f"File {file_path} not found. Returning default settings.")
            return cls()
        
        with open(file_path, 'r') as json_file:
            settings = json.load(json_file)
        
        db_settings = settings.get('database', {})
        return cls(**db_settings)

Base = declarative_base()

class AvtTask(Base):
    __tablename__ = 'avt_tasks'
    
    createdAt = Column(Integer, nullable=True)
    updatedAt = Column(Integer, nullable=True)
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Float, nullable=True)
    creator = Column(Text, nullable=True)
    task_param = Column(Text, nullable=True)
    task_stat = Column(Float, nullable=True)
    worker_ip = Column(Text, nullable=True)
    process_id = Column(Float, nullable=True)
    task_ETA = Column(Float, nullable=True)
    task_output = Column(Text, nullable=True)
    task_message = Column(Text, nullable=True)

class TaskConfig(Base):
    __tablename__ = 'task_config'
    
    createdAt = Column(Integer, nullable=True)
    updatedAt = Column(Integer, nullable=True)
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=True, unique=True)
    type = Column(Float, nullable=True)
    params = Column(Text, nullable=True)
    outputs = Column(Text, nullable=True)
    options = Column(Text, nullable=True)
    startBy = Column(Text, nullable=True)
    enable = Column(Boolean, nullable=True)
    contentHtml = Column(Text, nullable=True)
    order = Column(Float, nullable=True)

class Database:
    def __init__(self, host, port, user, password, db_name):
        self.db_url = self.create_db_url(host, port, user, password, db_name)
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.connected = False
        try:
            self.test_connection()
            print("Database connection established.")
            self.connected = True
        except Exception as e:
            print(f"Failed to connect to the database: {e}")

    @staticmethod
    def create_db_url(host, port, user, password, db_name):
        return f'postgresql://{user}:{password}@{host}:{port}/{db_name}'

    def add_task(self, task_type, creator, task_param=None, task_stat=None, worker_ip=None, process_id=None, task_ETA=None, task_output=None, task_message=None):
        session = self.Session()
        
        try:
            # Convert task_param to JSON string if it's a list of dictionaries
            param_json = json.dumps(task_param) if (isinstance(task_param, list) or isinstance(task_param, dict)) else task_param
            
            new_task = AvtTask(
                createdAt=int(datetime.now().timestamp()*1000),
                updatedAt=int(datetime.now().timestamp()*1000),
                type=task_type,
                creator=creator,
                task_param=param_json,
                task_stat=task_stat,
                worker_ip=worker_ip,
                process_id=process_id,
                task_ETA=task_ETA,
                task_output=task_output,
                task_message=task_message
            )
            session.add(new_task)
            session.commit()
            id = new_task.id  # Access the task_id before closing the session
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error adding task: {e}")
            id = None
        finally:
            session.close()
        
        return id

    def update_task(self, task_id, **kwargs):
        session = self.Session()
        
        try:
            task = session.query(AvtTask).filter_by(id=task_id).first()
            if not task:
                return False
            for key, value in kwargs.items():
                setattr(task, key, value)
            task.updatedAt = int(datetime.now().timestamp()*1000)
            session.commit()
            success = True
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error updating task: {e}")
            success = False
        finally:
            session.close()
        
        return success

    # def get_tasks(self, limit=None, offset=None):
    #     session = self.Session()
        
    #     try:
    #         query = session.query(AvtTask)
    #         if limit:
    #             query = query.limit(limit)
    #         if offset:
    #             query = query.offset(offset)
    #         tasks = query.all()
    #     except SQLAlchemyError as e:
    #         print(f"Error retrieving tasks: {e}")
    #         tasks = []
    #     finally:
    #         session.close()
        
    #     return tasks
    
    def get_tasks(self, limit=None, offset=None):
        session = self.Session()
        
        try:
            query = session.query(AvtTask).order_by(AvtTask.createdAt.desc())
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            tasks = query.all()
        except SQLAlchemyError as e:
            print(f"Error retrieving tasks: {e}")
            tasks = []
        finally:
            session.close()
        
        return tasks

    def add_task_config(self, name, task_type, params=None, outputs=None, options=None, startBy=None, enable=True, contentHtml=None, order=None):
        session = self.Session()
        
        try:
            params_json = json.dumps(params) if (isinstance(params, list) or isinstance(params, dict)) else params
            outputs_json = json.dumps(outputs) if (isinstance(outputs, list) or isinstance(outputs, dict)) else outputs
            
            new_config = TaskConfig(
                createdAt=int(datetime.now().timestamp()*1000),
                updatedAt=int(datetime.now().timestamp()*1000),
                name=name,
                type=task_type,
                params=params_json,
                outputs=outputs_json,
                options=options,
                startBy=startBy,
                enable=enable,
                contentHtml=contentHtml,
                order=order
            )
            session.add(new_config)
            session.commit()
            config_id = new_config.id  # Access the config_id before closing the session
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error adding task config: {e}")
            config_id = None
        finally:
            session.close()
        
        return config_id

    def update_task_config(self, config_id, **kwargs):
        session = self.Session()
        
        try:
            config = session.query(TaskConfig).filter_by(id=config_id).first()
            if not config:
                return False
            for key, value in kwargs.items():
                setattr(config, key, value)
            config.updatedAt = int(datetime.now().timestamp()*1000)
            session.commit()
            success = True
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error updating task config: {e}")
            success = False
        finally:
            session.close()
        
        return success

    def get_task_configs(self, limit=None, offset=None):
        session = self.Session()
        
        try:
            query = session.query(TaskConfig)
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            configs = query.all()
        except SQLAlchemyError as e:
            print(f"Error retrieving task configs: {e}")
            configs = []
        finally:
            session.close()
        
        return configs
    
    def test_connection(self):
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("Successfully connected to the database.")
        except exc.SQLAlchemyError as e:
            raise Exception(f"Database connection failed: {e}")
# Example usage
if __name__ == "__main__":

    db_config = DatabaseConfig().read_from_json("config.json")
    print(db_config.host, db_config.port)
    db = Database(db_config.host, db_config.port, db_config.user, db_config.password, db_config.database)
    
    task_param = [{"name":"main_image_file","value":"/data/tiff-data/quang_ninh_1m.tif"},{"name":"template_image_file","value":"/data/tiff-data/template/08_resized.png"}]
    
    # # Adding a new task
    task_id = db.add_task(
        task_type=7,
        creator='alex_123',
        task_param=task_param,
        task_stat=-5,
        worker_ip='127.0.0.1',
        process_id=123,
        task_ETA=3600,
        task_output='',
        task_message='New updateed task'
    )
    print(f"New task added with ID: {task_id}")
    
    # success = db.update_task(task_id=task_id, task_stat=10, task_output="updated output")
    # if success:
    #     print("success update task stat")
    # else:
    #     print("Error when update task stat")
    
    # Getting a list of tasks
    # tasks = db.get_tasks(limit=10)
    # for task in tasks:
    #     print(f"Task ID: {task.id}, Type: {task.type}, Creator: {task.creator}, param: {task.task_param}, type: {type(task.task_param)}")

    # # Adding a new task config
    # object_finder_param = [{"type":"file","name":"main_image_file","text":"","default":""},{"type":"file","name":"template_image_file","text":"","default":""}]
    # objct_finder_output = [{"type":"file","name":"result_image_file","text":"","default":"","value":""},{"type":"string","name":"rotated_bounding_box","text":"","default":"","value":""}]
    # config_id = db.add_task_config(
    #     name="object_finder",
    #     task_type=7,
    #     params=object_finder_param,
    #     outputs=objct_finder_output,
    #     options="{}",
    #     startBy="WorkerManager",
    #     enable=True,
    #     contentHtml="Tìm đối tượng từ ảnh mẫu",
    #     order=1.0
    # )
    # print(f"New task config added with ID: {config_id}")

    # Getting a list of task configs
    # configs = db.get_task_configs(limit=10)
    # for config in configs:
    #     print(f"Config ID: {config.id}, Name: {config.name}, Type: {config.type}")
