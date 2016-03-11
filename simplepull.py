from simplenote import Simplenote
import os, re, datetime, string
from diexylene.loader import *
import requests

di = Diary('full_entries/')

people = []
# Gather an array of people
for d in di.files:
	for e in d.entries:
		if not 'People' in e['extras']:
			continue
		for p in e['extras']['People']:
			if not p in people:
				people.append(p)

simplenote = Simplenote('user', 'pass')

sinceStamp = ''

with open('since','r') as f:
	sinceStamp = f.readline()

print 'Pulling entries since ' + sinceStamp + ' from simplenote.'

sinceFormat = '%Y-%m-%d-%H-%M'

since = datetime.datetime.strptime(sinceStamp,sinceFormat)
last = since

note_list = simplenote.get_note_list(since=since.strftime(sinceFormat))[0]

for note in note_list:
	noteId = note['key']

	full_note = simplenote.get_note(noteId)[0]

	try:
		lines = full_note['content'].split('\n')
	except:
		print full_note
		exit()

	entryTime = None
	header = lines[0]

	if 'Diary' == header or 'Dream' == header or 'AM' in header or 'PM' in header:
		entryTime = datetime.datetime.fromtimestamp(float(full_note['createdate']))

	if not entryTime:
		continue

	if entryTime > since:
		if entryTime > last:
			last = entryTime

		entry = {}
		entry['time'] = entryTime
		entry['text'] = ''
		entry['extras'] = {}
		for line in lines[1:]:
			if re.match(r'([A-Z][a-z]+):',line):
				tagType = re.match(r'([A-Z][a-z]+):',line).group(1)
				line = line[len(tagType) + 1:]
				entry['extras'][tagType] = line.split(',')

				continue
			
			entry['text'] += line + '\n'

		entry['text'] = entry['text'].strip()

		if header == 'Dream':
			entry['extras']['Tags'] = ['Dream']

			if not entry['text'][:6] == 'Dream.':
				entry['text'] = 'Dream. ' + entry['text']

		# reconstitute shortened people names
		if 'People' in entry['extras']:
			for i, person in enumerate(entry['extras']['People']):
				if not person[0] == '@':
					continue

				parts = re.split('([A-Z][a-z]*)', person[1:])
				parts = [x for x in parts if x != '']

				matches = []
				for p in people:
					names = p.split(' ')

					if not len(names) == len(parts):
						continue

					for n in range(len(parts)):
						if names[n][:len(parts[n])] == parts[n]:
							matches.append(p)

				if len(matches) == 0:
					print 'Could not find match for %s on day %s.' % (person, str(entryTime))
					entry['extras']['People'][i] = raw_input('What is their name? ')
				elif len(matches) > 1:
					print 'Multiple matches for %s on day %s.' % (person, str(entryTime))
					print matches
					choice = raw_input('Enter correct index: ')
					entry['extras']['People'][i] = matches[int(choice)]
				elif len(matches) == 1:
					entry['extras']['People'][i] = matches[0]

		# Download images
		if 'Photos' in entry['extras']:
			fixed = []
			for j,photo in enumerate(entry['extras']['Photos']):
				
				fileName = 'IMG_%d_%s.jpg' % (j,entryTime.strftime('%Y.%m.%d'))
				try:
					r = requests.get(photo.strip())
					with open('full_entries/Attachments/' + fileName,'wb') as f:
						f.write(r.content)
				except:
					print 'Download of %s failed.' % (photo)
				fixed.append(fileName)
			entry['extras']['Photos'] = fixed

			print 'Downloaded %d photos.' % (len(fixed))

		fileName = 'full_entries\\' + dateTimeToFileName(entryTime)
		if os.path.exists(fileName):
			
			day = Day.fromFile(fileName)
			found = False
			for current in day.entries:
				sample = entry['text'][:30]
				if sample in current['text']:
					found = True
			if not found:
				print 'Merged with: ' + fileName
				day.entries.append(entry)
				day.toFile(fileName)
			else:
				print "Entry already present for " + fileName
		else:
			print 'Creating file: ' + fileName
			day = Day()
			day.entries = [entry]
			day.date = entryTime
			day.toFile(fileName)

		simplenote.trash_note(noteId)

with open('since','w') as f:
	f.write(last.strftime(sinceFormat))

