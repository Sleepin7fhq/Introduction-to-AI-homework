import struct, io, json

class NestedFile(io.RawIOBase):
    def __init__(self, path, member):
        self.source = open(path,'rb')
        self.source.seek(member.header_offset)
        header=self.source.read(30)
        assert header[:4]==b'PK\x03\x04' and member.compress_type == 0
        name, extra = struct.unpack_from('<HH',header,26)
        self.start=member.header_offset + 30 + name + extra
        self.size=member.file_size
        self.position=0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        self.position = (0,self.position,self.size)[whence]+offset
        if self.position < 0: raise ValueError('negative seek')
        return self.position
    def read(self, length=-1):
        rest=max(0,self.size-self.position)
        count=min(length,rest) if length>=0 else rest
        self.source.seek(self.start+self.position)
        data=self.source.read(count)
        self.position += len(data)
        return data
    def close(self):
        self.source.close()
        super().close()
