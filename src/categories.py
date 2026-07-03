# category_name,transaction_class,category_id

class Category:
	def __init__(self, category_name: str, transaction_class: str, category_id: int):
		self.category_name = category_name
		self.transaction_class = transaction_class
		self.category_id = category_id