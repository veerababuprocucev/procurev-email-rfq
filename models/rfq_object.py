class RFQObject:

    def __init__(
        self,
        buyer_email,
        buyer_name,
        item_description,
        specifications,
        quantity,
        uom,
        brand,
        delivery_date,
        delivery_location,
        attachment_type="",
        attachment_path=""
    ):

        self.buyer_email = buyer_email
        self.buyer_name = buyer_name
        self.item_description = item_description
        self.specifications = specifications
        self.quantity = quantity
        self.uom = uom
        self.brand = brand
        self.delivery_date = delivery_date
        self.delivery_location = delivery_location
        self.attachment_type = attachment_type
        self.attachment_path = attachment_path

    def to_dict(self):

        return {
            "buyer_email": self.buyer_email,
            "buyer_name": self.buyer_name,
            "item_description": self.item_description,
            "specifications": self.specifications,
            "quantity": self.quantity,
            "uom": self.uom,
            "brand": self.brand,
            "delivery_date": self.delivery_date,
            "delivery_location": self.delivery_location,
            "attachment_type": self.attachment_type,
            "attachment_path": self.attachment_path
        }