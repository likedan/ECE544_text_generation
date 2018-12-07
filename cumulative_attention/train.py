from torch.utils.data import DataLoader
import torch
from torch import nn
from FashionDataSet import FashionDataSet
from model import FashionSentenceGenerator
import os
from tqdm import tqdm
import torch.multiprocessing as mp

BATCH_SIZE = 5
EPOCH_SIZE = 64
MEMORY_SIZE = 8
MODEL_DIRECTORY = './model.pth'
print(os.getcwd())
device = torch.device("cpu")
train_dataset = FashionDataSet('../dataset/train_dataset.p')
test_dataset = FashionDataSet('../dataset/test_dataset.p')

word_lang = train_dataset.word_lang

model = FashionSentenceGenerator(train_dataset.num_normal_word, word_lang.n_words - train_dataset.num_normal_word,
                                     train_dataset.MAX_LENGTH, batch_size=BATCH_SIZE)
if os.path.exists(MODEL_DIRECTORY):
    model.load_state_dict(torch.load(MODEL_DIRECTORY))
    print("Successfully load from previous results.")

model.share_memory()
criterion_sentence = nn.NLLLoss()
criterion_gating = nn.BCELoss()
decoder_optimizer = torch.optim.Adam(model.parameters())


def train(model, save_every_batch_num=1000, epoch_size=EPOCH_SIZE, batch_size=BATCH_SIZE, shuffle=True, num_workers=0, gate_coefficient=20):
    train_data_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=shuffle, num_workers=num_workers, drop_last=True)
    test_data_loader = DataLoader(test_dataset, batch_size=batch_size, num_workers=num_workers, drop_last=True)
    for i in tqdm(range(1, epoch_size + 1)):
        print("Running epoch ", str(i))
        for i_batch, sampled_batch in tqdm(enumerate(train_data_loader)):
            decoder_optimizer.zero_grad()
            loss, g_history = model(sampled_batch)
            for i in range(batch_size):
                loss += gate_coefficient * criterion_gating(g_history[i], sampled_batch['g_truth'][i])
            loss.backward()
            decoder_optimizer.step()

            if i_batch % save_every_batch_num == 0:
                torch.save(model.state_dict(), "model.pth")
                print("saved model")

        torch.save(model.state_dict(), "model.pth")
        print("saved model")
        # Validation
        with torch.set_grad_enabled(False):
            validation_loss = 0
            for i_batch, sampled_batch in enumerate(test_data_loader):
                loss, g_history = model(sampled_batch)
                for i in range(batch_size):
                    loss += gate_coefficient * criterion_gating(g_history[i], sampled_batch['g_truth'][i])
                validation_loss += loss
            with open('validation_loss.txt', 'a+') as f:
                f.write(str(validation_loss) + '\n')
            print(validation_loss)



processes = []
for i in range(1): # No. of processes
    p = mp.Process(target=train, args=(model,))
    p.start()
    processes.append(p)
for p in processes: p.join()