from enum import Enum

class AccountStatus(str, Enum):
    ACTIVE = "Active"
    CLOSED = "Closed"
    SUSPENDED = "Suspended"


class TransactionType(str, Enum):
    DEPOSIT = "Deposit"
    WITHDRAWAL = "Withdrawal"
    TRANSFER_IN = "Transfer In"
    TRANSFER_OUT = "Transfer Out"
    DEPOSIT_REVERSAL = "Deposit Reversal"
    WITHDRAWAL_REVERSAL = "Withdrawal Reversal"
    TRANSFER_IN_REVERSAL = "Transfer_in Reversal"
    TRANSFER_OUT_REVERSAL = "Transfer_out Reversal"



class TransactionReferencePrefix(str, Enum):
    DEPOSIT = "DEP"
    WITHDRAWAL = "WDL"
    TRANSFER = "TRF"
    REVERSAL= "REV"

    

class TransactionStatus(str, Enum):
    SUCCESS = "Success"
    FAILED = "Failed"
    REVERSED = "Reversed"