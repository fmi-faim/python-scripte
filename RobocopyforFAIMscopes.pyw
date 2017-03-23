# -*- coding: utf-8 -*-

import ctypes, datetime, getpass, os, psutil, re, subprocess, sys, shutil, threading, tkMessageBox
from filecmp import dircmp
import filecmp
from time import sleep
from Tkinter import Checkbutton, Button, Entry, Label, Text, Tk, StringVar, DoubleVar, IntVar, RIDGE, X, LEFT


def mainProg(pathSrc, pathDst1, pathDst2, multiThread, timeInterval, silentThread, deleteSource, mailAdresse):
	print (pathSrc+"; "+pathDst1+"; "+pathDst2+"; "+str(multiThread)+"; "+str(timeInterval)+"; "+str(silentThread)+"; "+str(deleteSource)+"; "+mailAdresse)
	# test number of destination entered				
	numdest = 0
	if (pathDst1 != "") | (pathDst2 != ""):
		numdest = 1
		#ThreadTwo = False
	if (pathDst1 != "") & (pathDst2 != ""):
		numdest = 2
		#ThreadTwo = True
	# If only one destination enterd, attribute it to pathDst1
	if numdest==1:
		if pathDst1 == "":
			pathDst1 = pathDst2
			pathDst2 = ""
	# Initialize the summary report
	summary = "Robocopy Folders:\n\nSource = "+pathSrc+"\n<p>Target1 = "+pathDst1+"\n<p>Target2 = "+pathDst2+"\n<p>"
	# Define the path for saving the Log file
	userName = getpass.getuser()
	if userName == "CVUser":
		logFilepath = r"C:\\Users\\CVUser\\Desktop\\Robocopy FAIM Logfiles"
	else:
		logFilepath = r"\\argon\\"+ userName + r"\\Desktop"
		if os.path.exists(logFilepath) == False:
			logFilepath = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
	logfileName = logFilepath + r"\\Robocopy Logfile_Started at " + datetime.datetime.now().strftime("%H-%M-%S") + ".html"
	# Edit summary
	summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Process started") 
	# Starts the copy with Robocopy
	# initialise Threads
	global Thread1
	Thread1 = threading.Thread()
	global Thread2
	Thread2 = threading.Thread()
	condition = False
	try:
		while condition == False:
			# ****Start Thread1********
			# Checks first that Thread1 is not running, otherwise skip the step.
			if Thread1.isAlive() == False:
				try:
					Thread1 = threading.Thread(target=worker, args=(pathSrc, pathDst1, silentThread))
					Thread1.start()
					summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Copying to destination 1")
				except:
					summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Problem with thread 1")
					SendEmail(mailAdresse, "Robocopy Info: ERROR", "Please check Summary")
					
			# Start second thread if pathDst2 exists
			if pathDst2 != "":
				if multiThread == 0:
					# wait for Thread1 to be finished before starting Thread2
					conditionWait = False
					while conditionWait == False:
						if not Thread1.isAlive():
							conditionWait = True
						else:
							summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: \tWaiting for Robocopy to finish dst1 before starting dst2...")
							sleep(10)	
					# Start Thread2 now that Thread1 is done
					if Thread2.isAlive() == False:
						try:
							Thread2 = threading.Thread(target=worker, args=(pathSrc, pathDst2, silentThread))
							Thread2.start()
							summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Copying to destination 2")
						except:
							summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Problem with thread 1")
							SendEmail(mailAdresse, "Robocopy Info: ERROR", "Please check Summary")
						
				else:
					# Start Thread2 in parallel to Thread1
					if Thread2.isAlive() == False:
						try:
							Thread2 = threading.Thread(target=worker, args=(pathSrc, pathDst2, silentThread))
							Thread2.start()
							summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Copying to destination2")
						except:
							summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Problem with thread 2")
							SendEmail(mailAdresse, "Robocopy Info: ERROR", "Please check Summary")
			
			# Wait next time-point before comparing folders
			summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Waiting for "+str(timeInterval)+" min before comparing folders again")
			sleep(int(timeInterval*60))
			# Delete files in source folder
			if deleteSource:
				# NB: If pathDst1 is not connected, no deletion accurs.
				# The script deletes first each file one by one and then goes once more through folders
				try:
					for root, directories, files in os.walk(pathSrc):
						for myFile in files:
							path1 = os.path.join(root, myFile)
							path2 = re.sub(pathSrc, pathDst1, path1)
							if os.path.isfile(path2) & filecmp.cmp(path1, path2)==True:
								os.remove(path1)
				except:
					summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Problem with deleting files\n")
					SendEmail(mailAdresse, "Robocopy Info: ERROR", "Please check Summary")
				# 	
				# Now empty folders are deleted...	
				emptyFolders = []
				try:
					for root, directories, files in os.walk(pathSrc):
						emptyFolders.append(root)
					emptyFolders.sort(reverse = True)
					for emptyFolder in emptyFolders[:-1]:
						if os.listdir(emptyFolder) == []:
							shutil.rmtree(emptyFolder)
				except:
					summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Problem with deleting folders\n")
					

			# Compare source and destination folders to determine whether process should be stopped (i.e. no new file created in Source folder)
			# If no new file or folder was created since the beginning of the robocopy, then the condition is true and loop is terminated (= exit)
			#
			# Starts by checking if dst1 still connected and then compare content of folders
			if os.path.exists(pathDst1):
				sameContent = compsubfolders(pathSrc, pathDst1)
				if sameContent==True:
					summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: All files in source were found in destination 1")
					# Continues with dst2 if it exists
					if pathDst2 != "":
						if os.path.exists(pathDst2):
							sameContent = compsubfolders(pathSrc, pathDst1)
							if sameContent==True:
								summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: All files in source were found in destination 2")
								# Everything went fine both for dst1 and dst2 and there was no change during time lapse indicated
								condition = True
						else:
							summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Problem with comparing files in dst2\nCould not find dst2 folder")
							SendEmail(mailAdresse, "Robocopy Info: ERROR", "Please check Summary")
							# Everything went fine for dst1, dst2 seems not available anymore
							condition = True
					else :
						# Everything went fine for dst1 (no dst2 had been entered by user) and there was no change during time lapse indicated
						condition = True
			elif pathDst2 != "":
				summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Problem with comparing files in dst1\nCould not find dst1 folder\nChecking now dst2\n")
				SendEmail(mailAdresse, "Robocopy Info: ERROR", "Please check Summary")
				if os.path.exists(pathDst2):
					sameContent = compsubfolders(pathSrc, pathDst1)
					if sameContent==True:
						summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: All files in source were found in destination 2")
						# dst1 could not be found anymore, but there is a copy on dst2 and no change during time lapse indicated
						condition = True
				else :
					summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Problem with comparing files in dst2\nCould not find dst2 either\n")
					SendEmail(mailAdresse, "Robocopy Info: ERROR", "Please check Summary")
					# Both destinations are not available anymore
					condition = True
			else:
				summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Problem with comparing files in dst1\nCould not find dst1 folder.\nRobocopy process aborted")
				SendEmail(mailAdresse, "Robocopy Info: ERROR", "Please check Summary")
				# dst1 is not available anymore, no dst2 had been entered
				condition = True
	
	# Something went wrong at some unidentified step		
	except:
		summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: An error occured.\n")
		SendEmail(mailAdresse, "Robocopy Info: ERROR", "Please check Summary")
		
	# Copying dst1 to dst2, as dst1 should be local and less error prone and dst2 might miss some files.
	summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Copying from source to destination(s) finished")
	
	ThreadThree = False
	if pathDst2 != "":
		sameContent = compsubfolders(pathDst1, pathDst2)
		if sameContent==False:
			try:
				Thread3 = threading.Thread(target=worker, args=(pathDst1, pathDst2, silentThread))
				Thread3.start()
				summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Copying missing files from destination 1 to destination 2")
				ThreadThree = True
			except:
				summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Problem with thread3 (dst1 to dst2)")
				SendEmail(mailAdresse, "Robocopy Info: ERROR", "Please check Summary")
		else:
			summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: destination 1 and destination 2 were checked and have same content")

	# Wait for copying from dest1 to dest2 to be finished
	conditionWait = False
	while conditionWait == False:
		if ThreadThree:
			if not Thread3.isAlive():
				conditionWait = True
			else:
				summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: \tCopying from destination 1 to destination 2 still active... Waiting 10sec more...")
				sleep(10)
		else:
			conditionWait = True
	
	# count number of files in each folder
	try:
		nbFiles = sum([len(files) for r, d, files in os.walk(pathSrc)])
		summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Number of files in source = "+str(nbFiles))
	except:
		summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Number of files in source could not be checked")
	try:
		nbFiles = sum([len(files) for r, d, files in os.walk(pathDst1)])
		summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Number of files in destination 1 = "+str(nbFiles))
	except:
		summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Number of files in destination 1 could not be checked")
	if pathDst2 != "":
		try:
			nbFiles = sum([len(files) for r, d, files in os.walk(pathDst2)])
			summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Number of files in destination 2 = "+str(nbFiles))
		except:
			summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Number of files in destination 2 could not be checked")
	
	summary = editSummary(logfileName, summary, "\n<p>%H:%M:%S: Process finished.")
	
	# Send E-mail at the end with the summary
	summary = re.sub("<p>", "", summary)
	dialogSummary.set("Process finished")
	SendEmail(mailAdresse, "Robocopy Info", summary)
	
	# In case e-mail could not be sent, summary is printed in Spyder console
	print summary
	
# FUNCTION: Check if Thread is running
def TestThreads(number):
	pass

# FUNCTION: get User full name
def get_display_name():
    GetUserNameEx = ctypes.windll.secur32.GetUserNameExW
    NameDisplay = 3

    size = ctypes.pointer(ctypes.c_ulong(0))
    GetUserNameEx(NameDisplay, None, size)
    nameBuffer = ctypes.create_unicode_buffer(size.contents.value)
    GetUserNameEx(NameDisplay, nameBuffer, size)
    return nameBuffer.value

# FUNCTION: Sends a mail to the user about calculated times
def SendEmail(mailAdresse, mailObject, mailText):
	import smtplib
	from email.mime.text import MIMEText
	try:
		msg = MIMEText(mailText)
		msg['Subject'] = mailObject
		msg['From'] = "Robocopy@fmi.ch"
		msg['To'] = mailAdresse

		s = smtplib.SMTP('cas.fmi.ch')
		s.sendmail("laurent.gelman@fmi.ch", mailAdresse, msg.as_string())
		s.quit()
	except:
		print("Could not send e-mail")

# FUNCTIONs from dialog box
def chooseSrcDir():
    from tkFileDialog import askdirectory
    global pathSrc
    pathSrc = askdirectory(initialdir=currdir, title="Please select a directory")
    srcTxt.set(pathSrc)
				
def chooseDst1Dir():
    from tkFileDialog import askdirectory
    global pathDst1
    pathDst1 = askdirectory(initialdir=currdir, title="Please select a directory")
    dst1Txt.set(pathDst1)

def chooseDst2Dir():
    from tkFileDialog import askdirectory
    global pathDst2
    pathDst2 = askdirectory(initialdir=currdir, title="Please select a directory")
    dst2Txt.set(pathDst2)

# FUNCTIOn Do Copy!
def doCopy():
	# Checks that a source folder has been selected
	if srcTxt.get() == "":
	    root2 = Tk()
	    root2.withdraw()
	    tkMessageBox.showerror(title="Problem", message="You must select a source folder")
	    root2.destroy()
	# Checks that at least one destination folder has been selected				
	elif (dst1Txt.get() == "") & (dst2Txt.get() == ""):
		root2 = Tk()
		root2.withdraw()
		tkMessageBox.showerror(title="Problem", message="You must select at least one destination folder")
		root2.destroy()
	else:
		#root.destroy()
		mainThread = threading.Thread(target = mainProg, args = (srcTxt.get(), dst1Txt.get(), dst2Txt.get(), multiThr.get(), timeInt.get(), silentThr.get(), deleteSrc.get(), mail.get()))
		mainThread.start()
# FUNCTION Cancel		
def abort():
	print ("Dialog Canceled")
	root.destroy()
	try:
		Thread1.run = False
		Thread2.run = False
	except:
		pass
	for proc in psutil.process_iter():
		if proc.name() == "conhost.exe":
			process = psutil.Process(proc.pid)
			process.terminate()
			
	for proc in psutil.process_iter():
		if proc.name() == "Robocopy.exe":
			process = psutil.Process(proc.pid)
			process.terminate()
	"""
	for proc in psutil.process_iter():
		if proc.name() == "python.exe":
			process = psutil.Process(proc.pid)
			process.terminate()
	"""
	process = psutil.Process()
	process.terminate()
	sys.exit()

# FUNCTION: Workers / Threads
def worker(var1, var2, silent):
	print ("worker started !!!")
	if silent==0:
		FNULL = open(os.devnull, 'w')
		subprocess.call(["robocopy", var1, var2, "/e", "/Z", "/r:0", "/w:30", "/COPY:DT", "/dcopy:T"], stdout=FNULL, stderr=subprocess.STDOUT)
	else:
		subprocess.call(["robocopy", var1, var2, "/e", "/Z", "/r:0", "/w:30", "/COPY:DT", "/dcopy:T"])

# FUNCTION compare subdirectories
def compsubfolders(source, destination):
	condition = True
	myComp = dircmp(source, destination)
	if len(myComp.left_only)!=0:
		condition = False
	for root, directories, files in os.walk(source):
		for myDir in directories:
			path1 = os.path.join(root, myDir)
			path2 = re.sub(source, destination, path1)
			if os.path.exists(path2):
				myComp = dircmp(path1, path2)
				if len(myComp.left_only)!=0:
					condition = False
			else:
				condition = False
	return condition
				
# FUNCTION TO DO: update summary and write logfile
def writeLogFile(logfileName, text):
	try:
		logfile = open(logfileName, 'w')
		logfile.write(text)
		logfile.close()
	except:
		print ("Problem with logfile: " +logfileName)

# FUNCTION Edit summary
def editSummary(logfileName, text1, text2):
	myTime = datetime.datetime.now()
	text1 += myTime.strftime(text2)
	writeLogFile(logfileName, text1)
	textTemp = re.sub("<p>", "", text1)
	dialogSummary.set(textTemp)
	return text1
	
	
# *******************************
# DIALOG WINDOW
# *******************************
process = psutil.Process()
# Dialog window
root = Tk()
root.title("Robocopy FAIM")
currdir = os.getcwd()
try:
	userName = get_display_name().split(",")
	mailAdresse = userName[1][1:]+"."+userName[0]+"@fmi.ch"
except:
	mailAdresse = "FirstName.LastName@fmi.ch"
# Source folder selection
srcTxt = StringVar()
srcTxt.set("")
srcButton = Button(root, text = 'Source directory', overrelief=RIDGE, font = "arial 10",  command=chooseSrcDir)
srcButton.config(bg = "light steel blue", fg="black")
srcButton.pack(padx = 10, pady=5, fill=X)
srcTxtLabel = Label(root, textvariable = srcTxt, font = "arial 10")
srcTxtLabel.config(bg = "light steel blue")
srcTxtLabel.pack(padx = 10, anchor = "w")
# Destination 1 folder selection
dst1Txt = StringVar()
dst1Txt.set("")
dst1Button = Button(root, text = 'Destination 1 directory', overrelief=RIDGE, font = "arial 10", command=chooseDst1Dir)
dst1Button.config(bg = "light steel blue", fg="black")
dst1Button.pack(padx = 10, pady=5, fill=X)
dst1TxtLabel = Label(root, textvariable = dst1Txt, font = "arial 10")
dst1TxtLabel.config(bg = "light steel blue")
dst1TxtLabel.pack(padx = 10, anchor = "w")
# Destination 2 folder selection
dst2Txt = StringVar()
dst2Txt.set("")
dst2Button = Button(root, text = 'Destination 2 directory', overrelief=RIDGE, font = "arial 10", command=chooseDst2Dir)
dst2Button.config(bg = "light steel blue")
dst2Button.pack(padx = 10, pady=5, fill=X)
dst2TxtLabel = Label(root, textvariable = dst2Txt, font = "arial 10")
dst2TxtLabel.config(bg = "light steel blue")
dst2TxtLabel.pack(padx = 10, anchor = "w")
# Options checkboxes
multiThr = IntVar()
multiThr.set(0)
multiCheckBox = Checkbutton(root, text="Copy both destinations in parallel", wraplength=200, variable=multiThr)
multiCheckBox.config(bg = "light steel blue", fg="black", justify = LEFT)
multiCheckBox.pack(padx = 10, pady=5, anchor="w")
silentThr = IntVar()
silentThr.set(0)
silentCheckBox = Checkbutton(root, text="Show Robocopy console", wraplength=200, variable=silentThr)
silentCheckBox.config(bg = "light steel blue", fg="black", justify = LEFT)
silentCheckBox.pack(padx = 10, pady=5, anchor="w")
deleteSrc = IntVar()
deleteSrc.set(0)
delCheckBox = Checkbutton(root, text="Delete files in source folder after copy", wraplength=200, variable=deleteSrc)
delCheckBox.config(bg = "light steel blue", fg="black", justify = LEFT)
delCheckBox.pack(padx = 10, pady=5, anchor="w")
# Time-lapse information
timeInt = DoubleVar()
timeInt.set(0.5)
tiLabel = Label(root, text="Time interval (min):", font = "arial 10")
tiLabel.config(bg = "light steel blue", fg="black")
tiLabel.pack(padx = 10, anchor="w")
tiText = Entry(root, width=6, justify=LEFT, textvariable = timeInt)
tiText.config(bg = "light steel blue", fg="black")
tiText.pack(padx = 10, anchor="w")
# E-mail information
mail = StringVar()
mail.set(mailAdresse)
sendLabel = Label(root, text="Send Info to:", font = "arial 10")
sendLabel.config(bg = "light steel blue", fg="black")
sendLabel.pack(padx = 10, pady= 5, anchor="w")
adresseText = Entry(root, justify=LEFT, width = 25, textvariable = mail)
adresseText.config(bg = "light steel blue", fg="black")
adresseText.pack(padx = 10, anchor="w")
# Summary
dialogSummary = StringVar()
dialogSummary.set("*** Summary window *****")
sumLabel = Label(root, textvariable=dialogSummary, font = "arial 10")
sumLabel.config(bg = "light steel blue", fg="navy", justify = LEFT, height = 12)
sumLabel.pack(padx = 10, pady= 10, anchor="w")
# Space
spaceLabel = Label(root, text=" ", font = "arial 10")
spaceLabel.config(bg = "light steel blue", fg="black")
spaceLabel.pack(padx = 15, anchor="w")
# Do Copy and Cancel buttons
doCopyButton = Button(root, text = 'Do Copy !', width = 8, overrelief=RIDGE, font = "arial 10", command = doCopy)
doCopyButton.config(bg = "lime green", fg="black")
doCopyButton.pack(side = "left", padx = 10, pady=5)
cancelButton = Button(root, text = 'Abort', width = 8, overrelief=RIDGE, font = "arial 10", command = abort)
cancelButton.config(bg = "red", fg="black")
cancelButton.pack(side = "right", padx = 10, pady=5)
root.config(bg="light steel blue")
# Show Dialog Window
root.mainloop()
