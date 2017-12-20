# Turk Books

The objective with this project is to create an accounting application that is almost entirely automated, easy to use, and will allow you to pull accurate reports.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

* Be sure to set the appropriate environment variables

### Installing

Start by cloning this repository

The Pipfile.lock contains all the dependancies for the project. If you already use [Pipenv](https://docs.pipenv.org/) you can run the following command and then go straight to running the program 

```
$ pipenv install
```

## Deployment

Personally I use Zappa

'''
$ zappa init
$ zappa deploy
'''

## Features

* Upload you receipts and bills to dropbox and have them automically parsed (using combination of OCR and Amazon Mechanical Turk) and then record the transactions to your accounting ledger ([Ledger-CLI](https://www.ledger-cli.org/)).

* If the transaction is a bill, once parsed it will create and send a check to the vendor using [Lob](https://lob.com)

## Future Developments

* This program doesn't even work yet so let's not get ahead of ourselves.
* Online Payments API?


## Built With

* [Flask](http://flask.pocoo.org/) - The web framework used
* [Ledger](https://www.ledger-cli.org/) - Command line accounting platform that parses plain text
* [Amazon Mechanical Turk](https://www.mturk.com/mturk/welcome) - Crowdsourcing platform for entering receipts, bills, etc.
* [Dropbox](https://www.dropbox.com/developers/reference/webhooks) - Dropbox webhooks (uploads receipts/bills to mturk)

## Authors

* **Matthew Sewell** - [Python Financial](https://pythonfinancial.com)

## License

This project is licensed under the MIT License

## Acknowledgments

* My mentor Darcy
