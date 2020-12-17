from datetime import datetime

class Logger:
    
    def __init__(self, log_file_path):
        self.file_path = log_file_path
        print(log_file_path)
        with open(log_file_path, 'w') as f:
            dt = datetime.now()
            f.write('[{0}] LOG FILE CREATED\n'.format(dt.ctime()))
        pass

    def write(self, log_string):
        #write log to file
        with open(self.file_path, 'a') as f:
            dt = datetime.now()
            f.write('[{0}] {1}\n'.format(dt.ctime(), log_string))

    def read(self) -> [str, list]:
        #read logs from file
        content=''
        with open(self.file_path, 'r') as f:
            content = f.readlines()
        return content

