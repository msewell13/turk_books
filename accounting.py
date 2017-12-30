from hashlib import sha256
from zappa.async import task
import hmac
from flask import Flask, request, render_template
import dropbox
from dropbox.files import FileMetadata
from dropbox.exceptions import ApiError
import os
import boto3
from boto.mturk.connection import MTurkConnection
from boto.mturk.connection import HTMLQuestion
import json
import requests


app = Flask(__name__)

# Instantiate Dropbox
dbx = dropbox.Dropbox(os.environ['DB_ACCESS_TOKEN'])

# Create connection to mturk
mtc = MTurkConnection(os.environ['AWS_ACCESS_KEY_ID'],
os.environ['AWS_SECRET_ACCESS_KEY'],
host = 'mechanicalturk.sandbox.amazonaws.com')


def send_email(email, name, subject, html, time, context, tags):
	with app.test_request_context():
		r = requests.post('https://api.mailgun.net/v3/{}/messages'.format(DOMAIN),
		                                    auth=auth,
		                                    data={"from": '{}@{}'.format(MAIL_PREFIX, DOMAIN),
		                                          "to": '{} <{}>'.format(name, email), 
		                                          "subject": subject,
		                                          "html": render_template(html, context=context),
		                                          "o:deliverytime": (datetime.utcnow() + timedelta(days=time)).strftime("%a, %d %b %Y %H:%M:%S +0000"),
		                                          "v:context": json.dumps(context),
		                                          "o:tag": tags})
		print('Status: {}, {}'.format(r.status_code, email))

# Check mturk account balance
def check_balance():
	try:
		account_balance = str(mtc.get_account_balance()[0])
		if float(account_balance[1:]) <= 10.00:
			print(account_balance)
			#send_email()
	except ValueError:
		print('You have an account balance of {0}'.format(account_balance))


def get_db_links(folder):
	'''Move the file to a temporary folder, get the shared url and then process
	the function that creates the HIT on Mechanical Turk'''

	temp_folder = '/matthew/business/atlasalliancegroup/pythonfinancial/receipts/temp/'
	result = dbx.files_list_folder(path=folder)
	for entry in result.entries:
		if isinstance(entry, FileMetadata):
			move_file = dbx.files_move_v2(from_path=entry.path_lower, to_path='{0}{1}'.format(temp_folder, entry.name))
			temp_location = move_file.metadata.path_lower
			try:
				doc_url = dbx.sharing_create_shared_link_with_settings(path=temp_location).url
			except ApiError:
				doc_url = dbx.sharing_list_shared_links(path=temp_location).links[0].url
			create_hit(doc_url, temp_location)



@task
def process_user(account):

	# Check Mturk account balance and notify if low
	check_balance()

	receipts_folder = '/matthew/business/atlasalliancegroup/pythonfinancial/receipts/'
	bills_folder = '/matthew/business/atlasalliancegroup/pythonfinancial/bills/'
	

	get_db_links(receipts_folder)
	# get_db_links(bills_folder)
			

	#dbx.files_permanently_delete(entry.path_lower)


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
			process_user(account)
	return ''



def create_hit(url, path):
	# Load the form template and set the height of the frame it will be shown in
	html_question = HTMLQuestion(render_template('form.html', url=url), 500)
	response = mtc.create_hit(question=html_question,
	                          max_assignments=1,
	                          title="Enter the information on a receipt",
	                          description="Help research a topic",
	                          keywords="question, answer, research, receipt, data entry",
	                          duration=120,
	                          reward=0.10)
	# The response included several fields that will be helpful later
	hit_type_id = response[0].HITTypeId
	hit_id = response[0].HITId
	print("Your HIT has been created. You can see it at this link:")
	print("https://workersandbox.mturk.com/mturk/preview?groupId={}".format(hit_type_id))
	print("Your HIT ID is: {}".format(hit_id))


## Future Developments

# Get responses from mturk and write them to our ledger file
def ledger():
		file = open('testfile.txt', 'a')
		file.write('{} ! {}\n'.format(form.date.data, form.note.data)) 
		file.write('    {}  {}\n'.format(form.to_account.data, form.to_amount.data))
		file.write('    {}  {}\n'.format(form.from_account.data, form.from_amount.data))
		file.close()

# Update form to allow adding of classes and payment types

if __name__ == '__main__':
	app.run(debug=True)


