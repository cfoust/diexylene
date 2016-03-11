
import os, re, datetime, sys, shutil, codecs
from diexylene.loader import *

from string import punctuation

def usage():
	print 'generator.py MM/DD/YY MM/DD/YY command [options]'
	print '             start    finish'
	print 'or'
	print 'generator.py yearn command [options]'
	print 'or'
	print 'generator.py all command [options]'

DATE_FORMAT = "%m/%d/%y"

def valiDate(date):
	try:
		datetime.datetime.strptime(date,DATE_FORMAT)
		return True
	except ValueError:
		return False

# Ensures the proper number of arguments
args = sys.argv[1:]

if len(args) < 1:
	print "ERR: Not enough arguments"
	usage()
	exit()


start = None
finish = None
if '/' in args[0] and '/' in args[1]:
	dates = []
	for date in args[:2]:
		if not valiDate(date):
			print "ERR: Invalid date: " + date
			usage()
			exit()
		else:
			dates.append(datetime.datetime.strptime(date,DATE_FORMAT))
	start = dates[0]
	finish = dates[1]
	args = args[2:]

elif 'year' in args[0]:
	if len(args[0]) < 5:
		print "ERR: Invalid year argument %s" % args[0]
		usage()
		exit()

	num = int(args[0][4:]) - 1

	if num < 0:
		print "ERR: Invalid year argument %d" % num
		usage()
		exit()
	if num < 2:
		if num == 0:
			start = datetime.datetime(2010,12,4)
		else:
			start = datetime.datetime(2011+num,1,28)
		finish = datetime.datetime(2011 + num + 1,1,27)
	else:
		if num == 2:
			start = datetime.datetime(2013,1,28)
		else:
			start = datetime.datetime(2013 + (num - 2),1,1)
		finish = datetime.datetime(2013 + (num - 2),12,31)

	args = args[1:]
elif 'all' == args[0]:
	start = datetime.datetime(2010,12,4)
	finish = datetime.datetime.today()
	args = args[1:]
elif 'l' == args[0][0]:
	# for lnt expressions
	# Like l6w means last six weeks
	# l3m means last 3 months
	# l2y means last 2 years (from today)

	if len(args[0]) < 3:
		print 'ERR: Invalid lnt string. Bad length.'
		exit()
	s = args[0]

	t = s[-1]
	n = int(s[1:-1])

	finish = datetime.datetime.today()
	if t == 'w':
		delta = datetime.timedelta(weeks = -1*n)
		start = finish + delta
	elif t == 'm':
		delta = datetime.timedelta(weeks = -1*n*4)
		start = finish + delta
	elif t == 'y':
		delta = datetime.timedelta(weeks = -1*n*4*52)
		start = finish + delta
	elif t == 'd':
		delta = datetime.timedelta(hours = -1*n*24)
		start = finish + delta
	else:
		print 'ERR: lnt type not recognized: "%s"' % t
		exit()
	args = args[1:]
else:
	usage()
	exit()

di = Diary('full_entries/')

# Filter out entries in the given range
eir = []
for file in di.files:
	if file.date >= start and file.date <= finish:
		eir.append(file)

print '%d total files found in range %s-%s.' % (len(eir),start.strftime(DATE_FORMAT),finish.strftime(DATE_FORMAT))
print ""

# Parse out the command and options
command = args[0]
options = {}
if len(args) > 1:
	for op in args[1:]:
		parts = op.split('=')
		if len(parts) != 2:
			print 'Invalid argument: "%s", skipping.' % op
			continue
		options[parts[0]] = parts[1]

# Interpret special options

wowlog = None
if 'wowlog' in options:
	try:
		wowlog = WoWlog(options['wowlog'])
	except:
		print 'Invalid WoW log file'
else:
	try:
		wowlog = WoWlog('data/Logger/Logger.lua')
	except:
		print 'Could not load default of Logger.lua'

gvlog = None
if 'gvlog' in options:
	try:
		gvlog = GVLog(options['gvlog'])
	except:
		print 'Invalid Google Voice directory'
else:
	try:
		gvlog = GVLog('data/Google Voice/Takeout/Voice/Calls/')
	except:
		print 'Could not load default of Takeout/Voice/Calls/ for Google Voice.'

def deltaToTime(dt):
	seconds = dt.seconds
	hours = seconds / 3600
	seconds -= 3600*hours
	minutes = seconds / 60
	seconds -= 60*minutes
	return "%02dd:%02dh:%02dm:%02ds" % (dt.days,hours, minutes, seconds)

def SecondsToClock(seconds):
    hours = seconds / 3600
    seconds -= 3600*hours
    minutes = seconds / 60
    seconds -= 60*minutes
    return "%02dh:%02dm:%02ds" % (hours, minutes, seconds)

if command == 'stats':
	total = 0
	totalEntries = 0
	totalDreams = 0

	longEntries = []
	longestEntry = [0,'']

	if wowlog:
		totalTime = datetime.timedelta(seconds=0)

	if gvlog:
		totalTexts = 0

	people = []
	for day in eir:
		r = re.compile(r'[{}]'.format(punctuation))
		for entry in day.entries:
			new = r.sub(' ',entry['text'])

			words = len(new.split())
			total += words

			if words > 100:
				longEntries.append(words)

			if words > longestEntry[0]:
				longestEntry[0] = words
				longestEntry[1] = day.name

			if 'Tags' in entry['extras']:
				if 'Dream' in entry['extras']['Tags']:
					totalDreams += 1

			if 'People' in entry['extras']:
				for person in entry['extras']['People']:
					if not person in people:
						people.append(person)

		if wowlog:
			log = None
			for wowday in wowlog.days:
				if wowday['day'] == day.date:
					log = wowday
					break
			if log:
				totalTime += log['played']

		totalEntries += len(day.entries)

	if gvlog:
		for person in gvlog.texts:
			for text in gvlog.texts[person]:
				if text['timestamp'] <= finish and text['timestamp'] >= start:
					totalTexts += 1

	print "Statistics Report"
	print "================="
	difference = finish - start
	print "Time period: %d days." % difference.days
	print "================="
	print "Total words: %d." % total
	print "Total entries: %d." % totalEntries
	print "Total dreams: %d." % totalDreams
	print "Total people: %d." % len(people)
	print "Longest entry: %d. (%s)" % (longestEntry[0],longestEntry[1])
	print "Average long entry length: %2f words." % (float(sum(longEntries))/float(len(longEntries)))

	if wowlog:
		print "Total WoW time for period: %s." % (deltaToTime(totalTime))

	if gvlog:
		print "Total texts in this period: %d." % (totalTexts)
elif command == 'export':
	folderName = 's%s-f%s' % (start.strftime('%m.%d.%y'),
		finish.strftime('%m.%d.%y')
	)
	outputDir = 'output/' + folderName + '/'
	if not os.path.exists(outputDir):
		os.makedirs(outputDir)
		os.makedirs(outputDir + 'Attachments')

	# Scan for attachments
	fixedPhotos = {}
	for day in eir:
		for entry in day.entries:
			if 'Photos' in entry['extras']:
				for photo in entry['extras']['Photos']:
					# Have to change up the file name for latex to work
					fixedPhoto = photo[:-4].replace('.','-') + '.jpg'
					shutil.copyfile('full_entries/Attachments/' + photo,outputDir + 'Attachments/' + fixedPhoto)
					fixedPhotos[photo] = fixedPhoto

	of = open(outputDir + 'output.tex','w')
	# of = codecs.open(outputDir + 'output.tex','w', 'utf-8')

	with open('output/header.tex','r') as f:
		of.write(f.read())

	eir = sorted(eir, key=lambda day: day.date)
	# The main affair
	for day in eir:

		# Have to do this to fix the zero padding
		theDay = day.date.strftime('%d')
		if theDay[0] == '0':
			theDay = theDay[1]

		stamp = day.date.strftime('%A ' + theDay + ' %B %Y')

		of.write('\subsection{%s}' % stamp)
		# \begin{flushleft} \textbf{World of Warcraft: }01h:28m:47s\end

		# Grab the WoW time
		if wowlog:
			run = True
			if 'wow' in options:
				if options['wow'] == 'false':
					run = False
			if run == True:
				log = None
				for wowday in wowlog.days:
					if wowday['day'] == day.date:
						log = wowday
						break
				if log:
					timePlayed = log['played'].seconds
					if timePlayed > 0:
						of.write('\n\\begin{flushleft} \\textbf{World of Warcraft: }%s\end{flushleft}' % SecondsToClock(timePlayed))

		for i, entry in enumerate(day.entries):
			of.write('\n\n')

			# Index people
			if 'People' in entry['extras']:
				for person in entry['extras']['People']:
					parts = person.split(' ')
					if len(parts) == 2:
						of.write('\index{%s, %s}' % (parts[1], parts[0]))
					else:
						of.write('\index{%s}' % person)
			try:
				timeStamp = entry['time'].strftime('%I:%M %p')
			except:
				timeStamp = entry['timestamp']
			if timeStamp[0] == '0':
				timeStamp = timeStamp[1:]

			of.write('\n%s ' % timeStamp)

			# Clean stuff up
			text = entry['text']
			for char in ['&','$','%','#','^','_']:
				text = text.replace(char,'\%s' % char)

			# Special dream syntax
			if 'Tags' in entry['extras']:
				if 'Dream' in entry['extras']['Tags']:
					of.write('\colorbox{black}{\\textcolor{white}{DREAM} } ')
					text = text[6:]
			try:
				of.write(text + '\n\n')
			except:
				print [text]
				exit()

			# Photos
			if 'Photos' in entry['extras']:
				for photo in entry['extras']['Photos']:
					of.write('\includegraphics[width=\linewidth]{%s}' % fixedPhotos[photo])

			if i < (len(day.entries) - 1):
				of.write('---')

	of.write('\n\n\printindex\n\end{document}')
	of.close()

	with open(outputDir + 'build.bat', 'w') as f:
		f.write('pdflatex output.tex\nmakeindex output.idx\npdflatex output.tex')

	print 'Exported range to ' + outputDir + '.'
elif command == 'simplepull':
	people = []
	for f in di.files:
		print f['extras']
		exit()
elif command == 'resort':
	for day in eir:
		day.toFile(day.name)