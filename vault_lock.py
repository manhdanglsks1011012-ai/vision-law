"""Only one Vision law window/process may write a vault at a time."""
from PyQt6.QtCore import QLockFile

class VaultLease:
    def __init__(self,root):
        self.root=root
        directory=root/'.vision-law';directory.mkdir(parents=True,exist_ok=True)
        self.lock=QLockFile(str(directory/'vault.lock'));self.lock.setStaleLockTime(0)
        if not self.lock.tryLock(0):
            raise RuntimeError('Vault đang được một phiên Vision law khác sử dụng, hoặc không có quyền ghi: '+str(root))
    def release(self):self.lock.unlock()
