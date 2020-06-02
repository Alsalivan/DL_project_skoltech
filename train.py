import torch
import torch.nn as nn
from torch.nn import functional as F


def run_epoch(model, optimizer, criterion, dataloader, epoch, mode='train', device = None):
  
    if mode == 'train':
        model.train()
    else:
        model.eval()

    epoch_loss = 0.0
    epoch_precision, epoch_recall, epoch_f1 = 0.0, 0.0, 0.0
    
    try:
        dataloader._form_tensors()
    except:
        raise RuntimeError('You use a weird type of dataset. It shoulb be DatasetBuilder.')

    for i, (starts, contexts, ends, labels) in enumerate(dataloader._form_tensors()):

        starts, contexts, ends = starts.to(device), contexts.to(device), ends.to(device)
        labels = labels.to(device)
        
        code_vector, y_pred = model(starts, contexts, ends)
        loss = criterion(y_pred, torch.argmax(labels, dim = 1))
        precision, recall, f1 = precision_recall_f1(y_pred, labels)
        
        if optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        epoch_loss += loss.item()
        epoch_precision += precision
        epoch_recall += recall
        epoch_f1 += f1

        break
    
    return epoch_loss / len(dataloader), epoch_precision / len(dataloader), epoch_recall / len(dataloader), epoch_f1 / len(dataloader)
    
def train(model, optimizer, criterion, train_loader, val_loader, epochs,
          scheduler=None, checkpoint=True):
    
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

    for epoch in range(epochs):

        train_loss, train_precision, train_recall, train_f1 = run_epoch(model, optimizer, criterion, train_loader, epoch, mode = 'train', device = DEVICE)
        val_loss, val_precision, val_recall, val_f1 = run_epoch(model, None, criterion, val_loader, epoch, mode = 'val', device = DEVICE)


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

        print(f'Epoch {epoch+1}: train loss - {round(train_loss,5)}, validation loss - {round(val_loss,5)}')
        print(f'\t precision - {round(val_precision,5)}, recall - {round(val_recall,5)}, f1_score - {round(val_f1,5)}')
        print('----------------------------------------------------------------------')
        
    return list_train_loss , list_val_loss, list_train_precision, list_val_precision, list_train_recall, list_val_recall, list_train_f1, list_val_f1