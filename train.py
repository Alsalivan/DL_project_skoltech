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
    epoch_tp, epoch_fp, epoch_fn = 0.0, 0.0, 0.0
    
    num_batches = 0
    for starts, contexts, ends, labels in dataloader:
      
        starts, contexts, ends = starts.to(device), contexts.to(device), ends.to(device)
        labels = labels.to(device)
        
        code_vector, y_pred = model(starts, contexts, ends)
        loss = criterion(y_pred, labels)
        tp, fp, fn = precision_recall_f1(y_pred, labels, idx2target_vocab)
        epoch_tp += tp
        epoch_fp += fp
        epoch_fn += fn
        
        if optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        epoch_loss += loss.item()
        
        num_batches += 1
        
        if early_stop:
            break
    
    num_batches = float(num_batches)
    epoch_tp, epoch_fp, epoch_fn = float(epoch_tp), float(epoch_fp), float(epoch_fn)
    epsilon = 1e-7
    precision = epoch_tp / (epoch_tp + epoch_fp + epsilon)
    recall = epoch_tp / (epoch_tp + epoch_fn + epsilon)
    f1 = 2 * precision * recall / (precision + recall + epsilon)

    return epoch_loss/num_batches, precision, recall, f1
    
def train(model, optimizer, criterion, train_loader, val_loader, test_loader, epochs, idx2target_vocab,
          scheduler=None, checkpoint=True, early_stop = False):
    
    list_train_loss = []
    list_val_loss = []
    list_train_precision = []
    list_val_precision = []
    list_train_recall = []
    list_val_recall = []
    list_train_f1 = []
    list_val_f1 = []
    
    best_val_f1 = float('+inf')

    DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model.to(DEVICE)
    criterion = criterion.to(DEVICE)
    
    for epoch in range(epochs):
      
        start_time = time()

        train_loss, train_precision, train_recall, train_f1 = run_epoch(model, optimizer, criterion, train_loader, epoch,idx2target_vocab, mode = 'train', device = DEVICE, early_stop = early_stop)
        val_loss, val_precision, val_recall, val_f1 = run_epoch(model, None, criterion, val_loader, epoch, idx2target_vocab, mode = 'val', device = DEVICE, early_stop = early_stop)
        test_loss, test_precision, test_recall, test_f1 = run_epoch(model, None, criterion, test_loader, epoch, idx2target_vocab, mode = 'val', device = DEVICE, early_stop = early_stop)


        list_train_loss.append(train_loss)
        list_val_loss.append(val_loss)

        list_train_precision.append(train_precision)
        list_val_precision.append(val_precision)

        list_train_recall.append(train_recall)
        list_val_recall.append(val_recall)

        list_train_f1.append(train_f1)
        list_val_f1.append(val_f1)
        
        # checkpoint
        if val_f1 < best_val_f1:
            best_val_f1 = val_f1
            
            if checkpoint:
                torch.save(model.state_dict(), './best_model.pth')
        
        if scheduler is not None:
            scheduler.step(val_loss)

        print('Epoch {}: train loss - {}, validation loss - {}'.format(epoch+1, round(train_loss,5), round(val_loss,5)))
        print('\t Validation: precision - {}, recall - {}, f1_score - {}'.format(round(val_precision,5), round(val_recall,5), round(val_f1,5)))
        print('\t Test: precision - {}, recall - {}, f1_score - {}'.format(round(test_precision,5), round(test_recall,5), round(test_f1,5)))
        print ('Elapsed time: %.3f' % (time() - start_time))
        print('----------------------------------------------------------------------')
        
    return list_train_loss , list_val_loss, list_train_precision, list_val_precision, list_train_recall, list_val_recall, list_train_f1, list_val_f1
