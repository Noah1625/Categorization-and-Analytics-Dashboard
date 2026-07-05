# category_name,monthly_budget,category_id

class Budget:
	def __init__(self, category_name: str, monthly_budget: float, category_id: int):
		self.category_name = category_name
		self.monthly_budget = monthly_budget
		self.category_id = category_id