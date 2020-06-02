import torch
import torch.nn as nn
from torch.nn import functional as F
from metrics import precision_recall_f1
from time import time

def run_epoch(model, optimizer, criterion, dataloader, epoch, idx2target_vocab, mode='train', device = None, early_stop = False):
  
    if mode == 'train':
        model.train()
    else:
        model.eval()

    epoch_loss = 0.0
    epoch_precision, epoch_recall, epoch_f1 = 0.0, 0.0, 0.0
    
    try:
        dataloader._form_tensors()
    except:
        raise RuntimeError('You use a weird type of dataset. It should be DatasetBuilder.')
        
    num_batches = 0
    for (starts, contexts, ends, labels) in dataloader._form_tensors():
      
        starts, contexts, ends = starts.to(device), contexts.to(device), ends.to(device)
        labels = labels.to(device)
        
        code_vector, y_pred = model(starts, contexts, ends)
        loss = criterion(y_pred, labels)
        precision, recall, f1 = precision_recall_f1(y_pred, labels, idx2target_vocab)
        
        if optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        epoch_loss += loss.item()
        epoch_precision += precision
        epoch_recall += recall
        epoch_f1 += f1
        
        num_batches += 1
        
        if early_stop:
            break
    
    num_batches = float(num_batches)

    return epoch_loss/num_batches, epoch_precision/num_batches, epoch_recall/num_batches, epoch_f1/num_batches
    
def train(model, optimizer, criterion, train_loader, val_loader, epochs, idx2target_vocab,
          scheduler=None, checkpoint=True, early_stop = False):
    
    list_train_loss = []
    list_val_loss = []
    list_train_precision = []
    list_val_precision = []
    list_train_recall = []
    list_val_recall = []
    list_train_f1 = []
    list_val_f1 = []
    
    best_val_loss = float('+inf')

    DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(DEVICE)
    criterion = criterion.to(DEVICE)
    
    for epoch in range(epochs):
      
        start_time = time()

        train_loss, train_precision, train_recall, train_f1 = run_epoch(model, optimizer, criterion, train_loader, epoch,idx2target_vocab, mode = 'train', device = DEVICE, early_stop = early_stop)
        val_loss, val_precision, val_recall, val_f1 = run_epoch(model, None, criterion, val_loader, epoch, idx2target_vocab, mode = 'val', device = DEVICE, early_stop = early_stop)


        list_train_loss.append(train_loss)
        list_val_loss.append(val_loss)

        list_train_precision.append(train_precision)
        list_val_precision.append(val_precision)

        list_train_recall.append(train_recall)
        list_val_recall.append(val_recall)

        list_train_f1.append(train_f1)
        list_val_f1.append(val_f1)
        
        # checkpoint
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            
            if checkpoint:
                torch.save(model.state_dict(), './best_model.pth')
        
        if scheduler is not None:
            scheduler.step(val_loss)

        #print (str(epoch+1) + 'th epoch processed in %.3f' % (time() - start_time))
        print('Epoch {}: train loss - {}, validation loss - {}'.format(epoch+1, round(train_loss,5), round(val_loss,5)))
        print('\t precision - {}, recall - {}, f1_score - {}'.format(round(val_precision,5), round(val_recall,5), round(val_f1,5)))
        print('----------------------------------------------------------------------')
        
    return list_train_loss , list_val_loss, list_train_precision, list_val_precision, list_train_recall, list_val_recall, list_train_f1, list_val_f1
