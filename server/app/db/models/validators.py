from pydantic import model_validator

from bson import ObjectId




class PyObjectId(ObjectId):

    def __get_pydantic_json_schema__(self, *args, **kwargs):

        return {

            "type": "string",

            "description": "MongoDB ObjectId",

        }


    @classmethod

    @model_validator(mode='before')

    def check_valid_objectid(cls, values):

        value = values.get('value')

        if value is not None and not isinstance(value, ObjectId):

            raise ValueError("Invalid ObjectId")

        return values

