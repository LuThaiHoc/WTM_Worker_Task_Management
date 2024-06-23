# Define exit codes as constants

# General exit code, for details: https://tldp.org/LDP/abs/html/exitcodes.html
EXIT_FINISHED = 0
EXIT_GENERAL_ERROR = 1 # Miscellaneous errors, such as "divide by zero" and other impermissible operations
EXIT_MISUSE_OF_SHELL_BUILT_IN = 2 # Missing keyword or command, or permission problem (and diff return code on a failed binary file comparison).
EXIT_COMMAND_CANNOT_EXCUTE = 126 # Permission problem or command is not an executable
EXIT_COMMAND_NOT_FOUND = 127 # Possible problem with $PATH or a typo
EXIT_INVALID_ARGUMENT_EXIT_CODE = 128 # Exit takes only integer args in the range 0 - 255 (see first footnote)
EXIT_SCRIPT_TERMINATED_BY_CONTROLC = 130 # 	Control-C is fatal error signal 2, (130 = 128 + 2)

# Software define exit code
EXIT_CANNOT_CONNECT_TO_DATABASE = 3
EXIT_INVALID_INPUT_AVT_TASK_ID = 4
EXIT_INVALID_MODULE_PARAMETERS = 5
EXIT_FTP_DOWNLOAD_ERROR = 6
EXIT_FTP_UPLOAD_ERROR = 7
EXIT_PROCESS_KILLED_BY_WTM = 8
EXIT_OTHERS_ERROR = 9

exit_code_messages = {
    EXIT_FINISHED : "Finished",
    
    EXIT_GENERAL_ERROR : "Miscellaneous errors, such as divide by zero and other impermissible operations",
    EXIT_MISUSE_OF_SHELL_BUILT_IN : "Missing keyword or command, or permission problem (and diff return code on a failed binary file comparison).",
    EXIT_COMMAND_CANNOT_EXCUTE : "Permission problem or command is not an executable",
    EXIT_COMMAND_NOT_FOUND : "Module not found",
    EXIT_INVALID_ARGUMENT_EXIT_CODE : "Exit takes only integer args in the range 0 - 255 (see first footnote)",
    EXIT_SCRIPT_TERMINATED_BY_CONTROLC : "	Control-C is fatal error signal 2, (130 = 128 + 2)",
    
    EXIT_CANNOT_CONNECT_TO_DATABASE : "Cannot connect to the database",
    EXIT_INVALID_INPUT_AVT_TASK_ID : "Invalid input task id",
    EXIT_INVALID_MODULE_PARAMETERS : "Invalid module parameters",
    EXIT_FTP_DOWNLOAD_ERROR : "FTP download error",
    EXIT_FTP_UPLOAD_ERROR : "FTP upload error",
    EXIT_PROCESS_KILLED_BY_WTM : "Process killed by WTM",
    EXIT_OTHERS_ERROR : "Others Error" 
}