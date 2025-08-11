import uuid_utils as uuid


def generate_uuid() -> str:
    """Generate a UUID7 string for database use."""
    return str(uuid.uuid7())


# def extract_frame_names(data):
#     results = []

#     if isinstance(data, dict):
#         for key, value in data.items():
#             if key == 'frame_name':
#                 results.append(value)
#             elif isinstance(value, (dict, list)):
#                 results.extend(extract_frame_names(value))
#     elif isinstance(data, list):
#         for item in data:
#             results.extend(extract_frame_names(item))

#     return results
