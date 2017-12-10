from hashlib import sha256
import hmac
import threading
from flask import Flask, request
import dropbox
import os
import boto
from boto.mturk.connection import MTurkConnection
from boto.mturk.connection import HTMLQuestion
import json


app = Flask(__name__)

#Create connection to mturk
mtc = MTurkConnection(os.environ['AWS_ACCESS_KEY_ID'],
os.environ['AWS_SECRET_ACCESS_KEY'],
host = 'mechanicalturk.sandbox.amazonaws.com')

#Create connection to dropbox
# dbx = dropbox.Dropbox(os.environ['DB_ACCESS_TOKEN'])


def send_email():
	return None

# Check mturk account balance
def check_balance():
	try:
		account_balance = str(mtc.get_account_balance()[0])
		if float(account_balance[1:]) <= 10.00:
			send_email()
	except ValueError:
		print('You are good to go')



def process_user(account):
	'''Call /files/list_folder for the given user ID and process any changes.'''

	# OAuth token for the user
	token = os.environ['DB_ACCESS_TOKEN']

	# cursor for the user (None the first time)
	cursor = None

	dbx = dropbox.Dropbox(token)
	has_more = True

	while has_more:
		if cursor is None:
			result = dbx.files_list_folder(path='')
		else:
			result = dbx.files_list_folder_continue(cursor)

		for entry in result.entries:
			# Ignore deleted files, folders, and non-markdown files
			if (isinstance(entry, DeletedMetadata) or
				isinstance(entry, FolderMetadata) or
				not entry.path_lower.endswith('.md')):
				continue

			# Convert to Markdown and store as <basename>.html
			_, resp = dbx.files_download(entry.path_lower)
			html = markdown(resp.content)
			dbx.files_upload(html, entry.path_lower[:-3] + '.html', mode=WriteMode('overwrite'))

		# Update cursor
		cursor = result.cursor
		redis_client.hset('cursors', account, cursor)

		# Repeat only if there's more to do
		has_more = result.has_more



@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
	'''Receive a list of changed user IDs from Dropbox and process each.'''

	if request.method == 'GET':
		return request.args.get('challenge')
	else:
		# Make sure this is a valid request from Dropbox
		signature = request.headers.get('X-Dropbox-Signature')
		if not hmac.compare_digest(signature, hmac.new(os.environ['DB_APP_SECRET'].encode('UTF-8'), request.data, sha256).hexdigest()):
			abort(403)

		for account in json.loads(request.data)['list_folder']['accounts']:
			# We need to respond quickly to the webhook request, so we do the
			# actual work in a separate thread. For more robustness, it's a
			# good idea to add the work to a reliable queue and process the queue
			# in a worker process.
			threading.Thread(target=process_user, args=(account,)).start()
	return ''



def mturk_receipts():
	question_html_value = """
	<html>
	<head>
	<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'/>
	<script src='https://s3.amazonaws.com/mturk-public/externalHIT_v1.js' type='text/javascript'></script>
	</head>
	<body>
	<!-- HTML to handle creating the HIT form -->
	<form name='mturk_form' method='post' id='mturk_form' action='https://workersandbox.mturk.com/mturk/externalSubmit'>
	<input type='hidden' value='' name='assignmentId' id='assignmentId'/>
	<!-- This is where you define your question(s) --> 
	<h1>Who is the vendor (name of the company) on the receipt?</h1>
	<p><textarea name='answer' rows=3 cols=80></textarea></p>
	<h1>What is the date of the transaction?</h1>
	<p><textarea name='answer' rows=3 cols=80></textarea></p>
	<h1>What is the total amount of the transaction?</h1>
	<p><textarea name='answer' rows=3 cols=80></textarea></p>
	<h1>What was the method of payment for this transaction?</h1>
	<select name="Method of Payment">
	  <option value="Amex">Amex ending in 1006</option>
	  <option value="MasterCard">MC ending in 1726</option>
	  <option value="Cash">Cash</option>
	  <option value="Other">Other/Unknown</option>
	</select>
	<h1>What is the expense class? (This will be handwritten on the top of the reciept or highlighted.)</h1>
	<select name="Class">
	  <option value="2013 E. Mallon">2013 E. Mallon</option>
	  <option value="45 Acres">45 Acres</option>
	  <option value="Fernan 20 Acres">Fernan 20 Acres</option>
	  <option value="AMA">Other/Unknown</option>
	</select>
	<!-- HTML to handle submitting the HIT -->
	<p><input type='submit' id='submitButton' value='Submit' /></p></form>
	<script language='Javascript'>turkSetAssignmentID();</script>
	</body>
	</html>
	"""
	# The first parameter is the HTML content
	# The second is the height of the frame it will be shown in
	# Check out the documentation on HTMLQuestion for more details
	html_question = HTMLQuestion(question_html_value, 500)
	# These parameters define the HIT that will be created
	# question is what we defined above
	# max_assignments is the # of unique Workers you're requesting
	# title, description, and keywords help Workers find your HIT
	# duration is the # of seconds Workers have to complete your HIT
	# reward is what Workers will be paid when you approve their work
	# Check out the documentation on CreateHIT for more details
	response = mtc.create_hit(question=html_question,
	                          max_assignments=1,
	                          title="Enter the information on a receipt",
	                          description="Help research a topic",
	                          keywords="question, answer, research, receipt, data entry",
	                          duration=120,
	                          reward=0.50)
	# The response included several fields that will be helpful later
	hit_type_id = response[0].HITTypeId
	hit_id = response[0].HITId
	print("Your HIT has been created. You can see it at this link:")
	print("https://workersandbox.mturk.com/mturk/preview?groupId={}".format(hit_type_id))
	print("Your HIT ID is: {}".format(hit_id))

if __name__ == '__main__':
	app.run()


