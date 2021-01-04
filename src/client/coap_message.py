from src.client.exceptions import InvalidFormat


class CoAPMessage:
    """
    Encapsulates a CoAP-style message, providing an easy means of accessing all header fields.
    Is responsible for validating messages and throws exceptions in case of incorrect formats.
    """

    def __init__(self, payload: str, msg_type: int, msg_class: int, msg_code: int, msg_id: int,
                 header_version=0x1, token_length=0x0, token=0x0):
        self.payload = payload
        self.header_version = header_version
        self.msg_type = msg_type
        self.token_length = token_length
        self.msg_class = msg_class
        self.msg_code = msg_code
        self.msg_id = msg_id
        self.token = token

    def __str__(self) -> str:
        return f"""[VERSION]:\t{self.header_version}\n[TYPE]:\t\t{self.msg_type}\n[TKN LEN]:\t{self.token_length}
[CLASS]:\t{self.msg_class}\n[CODE]:\t\t{self.msg_code}\n[MSG ID]:\t{self.msg_id}
[TOKEN]:\t{hex(self.token) if self.token_length else ''}
[PAYLOAD]:\t{self.payload}\n"""

    @classmethod
    def from_bytes(cls, data_bytes: bytes) -> 'CoAPMessage':
        """
        Creates a CoAPMessage from bytes encoded using the CoAP protocol.
        This method will also check any format inconsistencies according to RFC-7252 and will throw InvalidFormat.

        :param data_bytes: The bytes that encode the message.
        """
        header_bytes = data_bytes[0:4]
        header_version = (0xC0 & header_bytes[0]) >> 6
        msg_type = (0x30 & header_bytes[0]) >> 4
        token_length = (0x0F & header_bytes[0]) >> 0
        msg_class = (header_bytes[1] >> 5) & 0x07
        msg_code = (header_bytes[1] >> 0) & 0x1F
        msg_id = (header_bytes[2] << 8) | header_bytes[3]
        # message must have correct header version, token length and class
        if header_version != 0x1:
            raise InvalidFormat("Message has incorrect CoAP header version")
        elif 9 <= token_length <= 15:
            raise InvalidFormat("Message has incorrect CoAP token length")
        elif msg_class in (1, 6, 7):
            raise InvalidFormat("Message uses reserved CoAP message class")
        # check special message types/classes/codes
        if (msg_class == 0x0 and msg_code == 0x0) or msg_type == 0x3:
            # message must be emtpy
            if not CoAPMessage.is_empty(msg_class, msg_code, token_length, data_bytes):
                raise InvalidFormat("Incorrect format for EMPTY CoAP message")
            # empty message must be confirmable
            if msg_type == 0x1:
                raise InvalidFormat("Non-confirmable CoAP message cannot be EMPTY")
        token = 0x0
        if token_length:
            token = int.from_bytes(data_bytes[4:4 + token_length], 'big')
        payload = data_bytes[5 + token_length:].decode('utf-8')
        return cls(payload, msg_type, msg_class, msg_code, msg_id,
                   header_version=header_version, token_length=token_length, token=token)

    @staticmethod
    def is_empty(msg_class: int, msg_code: int, token_length: int, data_bytes: bytes) -> bool:
        return msg_class == 0x0 and msg_code == 0x0 and token_length == 0x0 and len(data_bytes) == 4


class CoAP:
    """
    Containts static methods that encode a specified message.
    according to the CoAP RFC-7252 specification.
    """

    HEADER_LEN = 4
    VERSION = 0x1E
    MSG_TYPE = 0x1C
    TOKEN_LENGTH = 0x18
    MSG_CLASS = 0x15
    MSG_CODE = 0x10
    MSG_ID = 0x00

    def __init__(self):
        raise NotImplemented(f"Cannot instantiate {self.__class__.__name__} class")

    @staticmethod
    def wrap(msg: CoAPMessage) -> bytes:
        """
        Takes a CoAPMessage object and converts it into a stream of bytes according to the CoAP protocol

        :param msg: The CoAPMEssage object to be encoded.
        :return: bytes representing the encoded message.
        """

        coap_header = CoAP.build_header(msg)
        payload = b''
        if len(msg.payload):
            payload = 0xFF.to_bytes(1, 'big') + msg.payload.encode('utf-8')
        return coap_header.to_bytes(CoAP.HEADER_LEN + msg.token_length, 'big') + payload

    @staticmethod
    def build_header(msg: CoAPMessage) -> int:
        header = 0x00
        header |= msg.header_version << CoAP.VERSION
        header |= (0b11 & msg.msg_type) << CoAP.MSG_TYPE
        header |= msg.token_length << CoAP.TOKEN_LENGTH
        header |= (0b111 & msg.msg_class) << CoAP.MSG_CLASS
        header |= (0x1F & msg.msg_code) << CoAP.MSG_CODE
        header |= (0xFFFF & msg.msg_id) << CoAP.MSG_ID
        if msg.token_length:
            header = (header << 8 * msg.token_length) | msg.token
        return header
