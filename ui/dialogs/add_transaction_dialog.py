from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
    QDateEdit,
    QDoubleSpinBox,
)
from PySide6.QtCore import QDate, QLocale

#GUI element to collect new transaction data
#just collects the data, does not interact with the database itself
#FOR NOW also used for the editing
class AddTransactionDialog(QDialog):
    
    def __init__(
        self, 
        categories: list[str] | None = None, 
        parent=None,
        initial_data: dict | None = None, #for edit mode
        title: str = 'Add transaction' #for edit mode
        ) -> None:
        super().__init__(parent)
        
        self.setWindowTitle("Add transaction")
        self.setModal(True) #no concurrent input outside of dialog possible
        
        categories = categories or []
        if 'Uncategorized' not in categories:
            categories = ['Uncategorized'] + categories
        
        main_layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        main_layout.addLayout(form_layout)
        
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate()) #default: today
        form_layout.addRow("Date: ", self.date_edit)
        
        self.amount_sel = QDoubleSpinBox()
        self.amount_sel.setLocale(QLocale.c()) #format with . instead of ,
        self.amount_sel.setDecimals(2)
        self.amount_sel.setRange(-1000000000, 1000000000) #just to have some limit, maybe change
        self.amount_sel.setSingleStep(1.0) 
        self.amount_sel.setValue(0.0)
        form_layout.addRow('Amount: ', self.amount_sel)
        
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.addItems(categories)
        self.category_input.setCurrentText('Uncategorized')
        form_layout.addRow('Category: ', self.category_input)
        
        #for now no name matching (as with the categories) intended, if we decide to do that we'd have to change this 
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('e.g. \"Family Mart\", \"Lukas\", etc.')
        form_layout.addRow('Name: ', self.name_input)
        
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText('optional Note')
        form_layout.addRow('Description: ', self.desc_input)
        
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton('Cancel')
        self.save_button = QPushButton('Save')
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self._save_input)
        
        #edit transaction mode:
        if initial_data:
            tx_date = initial_data.get('tx_date')
            if tx_date:
                d = QDate.fromString(tx_date, 'yyyy-MM-dd')
                if d.isValid():
                    self.date_edit.setDate(d)
            if initial_data.get('amount') is not None:
                self.amount_sel.setValue(float(initial_data['amount']))
            cat = initial_data.get['category']
            if cat: 
                self.category_input.setCurrentText(str(cat))
            name = initial_data.get('name')
            if name:
                self.name_input.setText(str(name))
            desc = initial_data.get('description')
            if desc:
                self.desc_input.setText(str(desc))
        
    
    # on 'save' button click  
    def _save_input(self) -> None:
        amount = self.amount_sel.value()
                
        if amount == 0.0:
            QMessageBox.warning(
                self, 
                'Invalid amount',
                'Amount may not be 0.'
            )
            return
        
        self.accept()
       
    
    # for outside use to get data from here
    def get_data(self) -> dict:
        return{
            "tx_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "amount": float(self.amount_sel.value()),
            "category": self.category_input.currentText().strip() or "Uncategorized",
            "name": self.name_input.text().strip() or None,
            "description": self.desc_input.text().strip() or None,
        }
                    
        
        

    