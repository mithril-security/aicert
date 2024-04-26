from datasets import load_dataset

dataset_name = 'Innermost47/alpaca-fr'
question_column = 'instruction'
answer_column = 'output'
number_elements_for_training = 40

load_dataset(dataset_name)
dataset = load_dataset(dataset_name)
dataset= dataset['train'].select(range(number_elements_for_training))
dataset = dataset.select_columns(['instruction', 'output'])
dataset.to_csv('tmp/datasets/alpaca-fr.csv')