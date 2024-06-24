import ftplib
from ftplib import FTP
from tqdm import tqdm
import os, json

class FtpConfig():
    def __init__(self,host="localhost", port=2, user="user", password="password"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        
    def save_to_json(self, file_path='config.json'):
        if not os.path.exists(file_path):
            settings = {}
        else:
            with open(file_path, 'r') as json_file:
                settings = json.load(json_file)

        settings['ftp'] = {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
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
        
        ftp_settings = settings.get('ftp', {})
        return cls(**ftp_settings)


def ftp_download(ftp_server, ftp_port, username, password, file_path, force_download=False):
    """
    Download a file from an FTP server.

    :param ftp_server: Address of the FTP server.
    :param ftp_port: Port number of the FTP server.
    :param username: Username for authentication.
    :param password: Password for authentication.
    :param file_path: Path to the file on the FTP server.
    :param force_download: Whether to force download the file even if it exists locally.
    :return: Path of the downloaded file on the local machine if download succeeds, otherwise None.
    """
    try:
        # Connect to the FTP server
        ftp = FTP()
        ftp.connect(host=ftp_server, port=ftp_port)
        ftp.login(user=username, passwd=password)

        # Get the file name from the file path
        filename = file_path.split('/')[-1]

        # Define the local path in the /tmp directory, creating corresponding directories
        local_dir = os.path.join('/tmp', os.path.dirname(file_path).lstrip('/'))
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)

        # Check if the file already exists
        if os.path.exists(local_path) and not force_download:
            print(f"File '{filename}' already exists at '{local_path}'.")
            return local_path

        # Get the size of the file
        file_size = ftp.size(file_path)

        # Open a local file to write the downloaded data to
        with open(local_path, 'wb') as local_file, tqdm(
            total=file_size,
            desc=f'Downloading {filename}',
            unit='B',
            unit_scale=True
        ) as progress:
            # Callback function to update progress bar
            def callback(data):
                local_file.write(data)
                progress.update(len(data))

            # Use RETR command to download the file
            ftp.retrbinary(cmd=f'RETR {file_path}', callback=callback)

        print(f"File '{filename}' downloaded successfully to '{local_path}'.")

        # Return the path of the downloaded file
        return local_path

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    finally:
        # Close the FTP connection
        if ftp:
            ftp.quit()



def ftp_upload(ftp_server, ftp_port, username, password, local_file_path, remote_directory):
    """
    Upload a file to an FTP server.

    :param ftp_server: Address of the FTP server.
    :param ftp_port: Port number of the FTP server.
    :param username: Username for authentication.
    :param password: Password for authentication.
    :param local_file_path: Path to the local file to upload.
    :param remote_directory: Path to the directory on the FTP server where the file will be uploaded.
    :return: File path in the FTP server if upload succeeds, otherwise None.
    """
    ftp = FTP()
    try:
        # Connect to the FTP server
        ftp.connect(host=ftp_server, port=ftp_port)
        ftp.login(user=username, passwd=password)

        # Change to the remote directory
        ftp.cwd(remote_directory)

        # Get the file name from the local file path
        filename = os.path.basename(local_file_path)

        # Get the size of the file
        file_size = os.path.getsize(local_file_path)

        # Open the local file to read the data
        with open(local_file_path, 'rb') as local_file, tqdm(
            total=file_size,  # Total size of the file for tqdm
            desc=f'Uploading {filename}',
            unit='B',
            unit_scale=True
        ) as progress:
            # Callback function to update progress bar
            def callback(data):
                progress.update(len(data))

            # Use STOR command to upload the file
            ftp.storbinary(cmd=f'STOR {filename}', fp=local_file, callback=callback)

        print(f"File '{filename}' uploaded successfully.")

        # Return the file path in the FTP server
        return os.path.join(remote_directory, filename)

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    finally:
        # Close the FTP connection
        if ftp:
            ftp.quit()
            
def get_server_checksum(ftp_server, ftp_port, username, password, file_path):
    """
    Get the checksum of a file on the FTP server without downloading it.

    :param ftp_server: Address of the FTP server.
    :param ftp_port: Port number of the FTP server.
    :param username: Username for authentication.
    :param password: Password for authentication.
    :param file_path: Path to the file on the FTP server.
    :return: Checksum of the file if supported and successful, otherwise None.
    """
    try:
        # Connect to the FTP server
        ftp = FTP()
        ftp.connect(host=ftp_server, port=ftp_port)
        ftp.login(user=username, passwd=password)

        # Check for supported features
        features = ftp.sendcmd("FEAT")
        print(features)
        checksum_command = None

        if "XMD5" in features:
            checksum_command = "XMD5"
        elif "XSHA1" in features:
            checksum_command = "XSHA1"
        elif "XSHA256" in features:
            checksum_command = "XSHA256"

        if not checksum_command:
            print("No checksum command supported by the FTP server.")
            return None

        # Get the checksum
        response = ftp.sendcmd(f"{checksum_command} {file_path}")
        checksum = response.split()[-1]
        
        print(f"{checksum_command} checksum of '{file_path}' is {checksum}")

        return checksum

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    finally:
        # Close the FTP connection
        if ftp:
            ftp.quit()
            
if __name__ == "__main__":
    ftp_config =FtpConfig().read_from_json("config.json")
    file_path = ftp_download(ftp_server=ftp_config.host, ftp_port=ftp_config.port, username=ftp_config.user, password=ftp_config.password, file_path="/data/tiff-data/quang_ninh_1m.tif", force_download=True)
    # file_path = ftp_upload(ftp_server=ftp_config.host, ftp_port=ftp_config.port, username=ftp_config.user, password=ftp_config.password, 
    #                        local_file_path="/tmp/output/22_result_image.png", remote_directory="/output/template_matching")
    
    if file_path is not None:
        print(file_path)
    