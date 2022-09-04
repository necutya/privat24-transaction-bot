import hashlib

import requests as requests
import xml.etree.ElementTree as ET


class Privat24Transaction:
    def __init__(self, amount: str, card_amount: str, rest: str, terminal: str, description: str):
        self.amount = amount
        self.card_amount = card_amount
        self.rest = rest
        self.terminal = terminal
        self.description = description

    def __str__(self):
        if "-" in self.card_amount:
            op = "😭"
        else:
            op = "🤑"

        return f"""{op}
    Amount: {self.card_amount}
    Rest: {self.rest}
    Terminal: {self.terminal}
    Description: {self.description}
"""


class Privat24Card:
    def __init__(self, card, balance):
        self.card = card
        self.balance = balance
        self.transactions = []

    def add_transaction(self, tr: Privat24Transaction):
        self.transactions.append(tr)

    def __str__(self):
        res = f"Card: {self.card}\nCurrent balance: {self.balance}\n"

        for transaction in self.transactions:
            res += transaction.__str__()

        return res


class Privat24:
    PRIVAT24_REQ = f'''<?xml version="1.0" encoding="UTF-8"?>
<request version="1.0">
    <merchant>
        <id>%s</id>
        <signature>%s</signature>
    </merchant>
    <data>%s</data>
</request>'''

    TRANSACTION_LIST_REQ_DATA = """<oper>cmt</oper>
        <wait>0</wait>
        <test>0</test>
        <payment id="">
            <prop name="sd" value="%s" />
            <prop name="ed" value="%s" />
            <prop name="card" value="%s" />
        </payment>"""

    BALANCE_REQ_DATA = """<oper>cmt</oper>
            <wait>0</wait>
            <test>0</test>
            <payment id="">
                <prop name="cardnum" value="%s" />
                <prop name="country" value="UA" />
            </payment>"""

    PRIVAT24_URL = "https://api.privatbank.ua/p24api"
    TRANSACTION_LIST_ENDPOINT = "/rest_fiz"
    BALANCE_ENDPOINT = "/balance"

    def __init__(self, merchant_id, merchant_password):
        self.merchant_id = merchant_id
        self.merchant_password = merchant_password

    @staticmethod
    def __get_up_signature(body: str, password: str) -> str:
        return hashlib.sha1(hashlib.md5((body + password).encode('utf-8')).hexdigest().encode('utf-8')).hexdigest()

    def get_balance(self, card_number: str) -> Privat24Card:
        body_data = self.BALANCE_REQ_DATA % card_number
        body = self.PRIVAT24_REQ % \
               (self.merchant_id, self.__get_up_signature(body_data, self.merchant_password), body_data)
        url = self.PRIVAT24_URL + self.BALANCE_ENDPOINT

        try:
            resp = requests.post(url, body)
        except requests.ConnectionError as e:
            raise Exception(f"Cannot get card balance: {e}")

        if resp.status_code != 200:
            raise Exception("Invalid status code while getting balance")

        try:
            xml_resp = ET.fromstring(resp.text)
            return Privat24Card(
                xml_resp.find('data/info/cardbalance/card/card_number').text,
                xml_resp.find('data/info/cardbalance/balance').text,
            )
        except Exception as e:
            raise Exception(f"Cannot parse card balance body ({resp.text}): {e}")

    def get_transaction_list(self, card_number: str, start_date: str, end_date: str) -> Privat24Card:
        card = self.get_balance(card_number)

        body_data = self.TRANSACTION_LIST_REQ_DATA % (start_date, end_date, card_number)
        body = self.PRIVAT24_REQ % \
               (self.merchant_id, self.__get_up_signature(body_data, self.merchant_password), body_data)
        url = self.PRIVAT24_URL + self.TRANSACTION_LIST_ENDPOINT

        try:
            resp = requests.post(url, body)
        except requests.ConnectionError as e:
            raise Exception(f"Cannot get transaction list balance: {e}")

        if resp.status_code != 200:
            raise Exception("Invalid status code while getting transaction list")

        try:
            xml_resp = ET.fromstring(resp.text)
            for st in xml_resp.findall('data/info/statements/statement'):
                if st.get('card'):
                    card.add_transaction(Privat24Transaction(
                        st.get('amount'),
                        st.get('cardamount'),
                        st.get('rest'),
                        st.get('terminal'),
                        st.get('description'),
                    ))
        except Exception as e:
            raise Exception(f"Cannot parse transaction list body ({resp.text}): {e}")

        return card
