import re
from typing import Any, Dict, List, Union


class PIIMasker:
    """
    Server-side PII sanitization engine.
    Redacts:
    - Vietnamese & standard phone numbers: (e.g. 0901234567 -> 09****4567, +84901234567 -> +849****567)
    - Bank Account Numbers: 9 to 16 consecutive digits or strings prefixed with ACC-
    """

    PHONE_REGEX = re.compile(r'(?:\+?84|0)(3[2-9]|5[6|8|9]|7[0|6-9]|8[1-9]|9[0-9])[0-9]{7}\b')
    ACCOUNT_REGEX = re.compile(r'\b(?:ACC-)?\d{9,16}\b')

    @classmethod
    def mask_string(cls, text: str) -> str:
        if not isinstance(text, str):
            return text

        # Mask phone numbers
        def mask_phone(match: re.Match) -> str:
            val = match.group(0)
            if len(val) >= 10:
                return val[:2] + "****" + val[-4:]
            return val[:2] + "****"

        # Mask account numbers
        def mask_account(match: re.Match) -> str:
            val = match.group(0)
            prefix = ""
            if val.startswith("ACC-"):
                prefix = "ACC-"
                val = val[4:]
            if len(val) >= 8:
                return prefix + val[:3] + "****" + val[-3:]
            return prefix + val[:2] + "****"

        text = cls.PHONE_REGEX.sub(mask_phone, text)
        text = cls.ACCOUNT_REGEX.sub(mask_account, text)
        return text

    @classmethod
    def sanitize(cls, data: Union[Dict[str, Any], List[Any], str, Any]) -> Any:
        if isinstance(data, dict):
            return {k: cls.sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.sanitize(item) for item in data]
        elif isinstance(data, str):
            return cls.mask_string(data)
        return data
