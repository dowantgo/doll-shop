class PaymentError(Exception):
    pass


class PaymentConfigurationError(PaymentError):
    pass


class PaymentNetworkError(PaymentError):
    pass


class PaymentSignatureError(PaymentError):
    pass
