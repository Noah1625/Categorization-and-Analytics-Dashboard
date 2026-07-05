# transaction_date,amount,description,transaction_type,category_id,transaction_code

class Transaction:
	def __init__(self, transaction_date: str, amount: float, description: str, transaction_type: str, category_id: int, transaction_code: str):
		self.transaction_date = transaction_date
		self.amount = amount
		self.description = description
		self.transaction_type = transaction_type
		self.category_id = category_id
		self.transaction_code = transaction_code