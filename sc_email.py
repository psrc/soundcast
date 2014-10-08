import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os.path

server = smtplib.SMTP('smtp.gmail.com', 587) #Gmail server
server.ehlo()
server.starttls()
server.ehlo()
server.login('soundcastpsrc', 'Multinomial') #Log in to Gmail account

def send_completion_email(recipient_list): #Sends email when model run is complete

    topsheet = 'R:/JOE/summarize/reports/Topsheet.xlsx'
    
    #Text part of the email
    msg = MIMEMultipart()
    msg['Subject'] = 'SoundCast Run Complete'
    text = 'This is to let you know that your SoundCast run is complete.\n\nAn Excel file containing some basic results is attached.'
    msg_text = MIMEText(text)
    msg.attach(msg_text)

    #Attach the Excel file
    ts = open(topsheet, 'rb')
    ts_file = MIMEBase('application', 'vnd.ms-excel')
    ts_file.set_payload(ts.read())
    encoders.encode_base64(ts_file)
    ts_file.add_header('Content-Disposition', 'attachment;filename=Topsheet.xlsx')
    msg.attach(ts_file)
    server.sendmail('soundcastpsrc@gmail.com', recipient_list, msg.as_string()) #Send email

def send_error_email(recipient_list, error_message = None): #Sends email when an error occurs

    log_files = ['soundcast_log.txt', 'skims_log.txt', 'truck_log.txt', 'last_run.log']

    msg = MIMEMultipart()
    msg['Subject'] = 'Error in SoundCast Run'
    text = 'Unfortunately, an error occured during your SoundCast run. Logfiles for your run are attached.'
    msg_text = MIMEText(text)
    msg.attach(msg_text)
    if error_message:
        err_msg = MIMEText(str(error_message))
        err_text = MIMEText('The error resulted in the following error message:\n')
        msg.attach(err_text)
        msg.attach(err_msg)

    for f in log_files:
        if not os.path.isfile(f):
            continue
        part = MIMEBase('application', 'plain')
        part.set_payload(open(f, 'rb').read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename=' + f)
        msg.attach(part)

    server.sendmail('soundcastpsrc@gmail.com', recipient_list, msg.as_string())