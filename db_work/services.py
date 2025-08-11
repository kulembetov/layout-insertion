import os
import json
from sqlalchemy import insert, select, update
from typing import List

from db_work.database import BaseManager
from db_work.utils import generate_uuid
from redis_cache.utils import get_cached_request


class PresentationLayoutManager(BaseManager):
    """Interacts With The PresentationLayout Table."""

    def __init__(self):
        super().__init__()

    def select_layout_by_name(self, name: str) -> bool | None:
        """Find a row in 'PresentationLayout' by name."""

        presentation_layout_table, session = self.open_session("PresentationLayout")

        def logic():

            query = select(presentation_layout_table).where(presentation_layout_table.c.name == name)
            result = session.execute(query).fetchone()
            if result:
                return True
            else:
                return False

        return super().execute(logic, session)

    def insert_new_layout(self, name: str) -> str | None:
        """Add new row in 'PresentationLayout'."""

        presentation_layout_table, session = self.open_session("PresentationLayout")

        def logic():
            uid = generate_uuid()
            values = {"id": uid, "name": name}
            query = insert(presentation_layout_table).values(values)
            session.execute(query)
            session.commit()
            return uid

        return super().execute(logic, session)


class ColorSettingsManager(BaseManager):
    """Interacts With The ColorSettings Table."""

    def __init__(self):
        super().__init__()

    def select_color_id(self) -> str | None:
        """Generate new color id."""

        color_settings_table, session = self.open_session("ColorSettings")

        def logic():
            new_color_id = generate_uuid()
            values = {"id": new_color_id, "count": 1, "lightenStep": 0.3, "darkenStep": 0.3, "saturationAdjust": 0.3}
            query = insert(color_settings_table).values(values)
            session.execute(query)
            session.commit()

            return new_color_id if new_color_id else None

        return super().execute(logic, session)


class PresentationLayoutStylesManager(BaseManager):
    """Interacts With The PresentationLayoutStyles Table."""

    def __init__(self):
        super().__init__()

    def insert_new_ids(self, presentation_layout_id: str | None, color_settings_id: str | None) -> str | None:
        """Inserts ColorSettingsID and PresentationLayoutID into PresentationLayoutStyles."""

        presentation_layout_styles_table, session = self.open_session("PresentationLayoutStyles")

        def logic():
            uid = generate_uuid()
            values = {"id": uid, "colorSettingsId": color_settings_id, "presentationLayoutId": presentation_layout_id}
            query = insert(presentation_layout_styles_table).values(values)
            session.execute(query)
            session.commit()
            return uid

        return super().execute(logic, session)
    

class SlideLayoutManager(BaseManager):

    def __init__(self):
        super().__init__()

    def extract_frame_data(self, data):
        """Recursive extraction from cache."""
        results = []
    
        def recursive_extract(obj):
            nonlocal results
            
            if isinstance(obj, dict):
                if all(key in obj for key in ['slide_number', 'frame_name', 'imagesCount', 'sentences', 'forGeneration', 'slide_type']):
                    result_dict = {
                        'number': obj.get('slide_number'),
                        'name': obj.get('frame_name'),
                        'imagesCount': obj.get('imagesCount'),
                        'sentences': obj.get('sentences'),
                        'forGeneration': obj.get('forGeneration'),
                        'isLast': obj.get('slide_type'),
                    }
                    results.append(result_dict)
                    
                for value in obj.values():
                    recursive_extract(value)
                    
            elif isinstance(obj, list):
                for item in obj:
                    recursive_extract(item)

        recursive_extract(data)
        return results

    def get_slide_layout_data_from_cache(self, presentation_layout_id: str) -> List[str] | None:
        """Get slide layout data from cahce and add extra fields."""

        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        json_file_path = os.path.join(parent_dir, 'output.json')
        with open(json_file_path, 'r', encoding='utf-8') as file:
            cache = json.load(file)
        # FIGMA_FILE_ID = os.getenv("FIGMA_FILE_ID")
        # cache = get_cached_request(FIGMA_FILE_ID)
        slide_layout_frame_data = self.extract_frame_data(cache)
        for item in slide_layout_frame_data:
            if item['isLast'] == 'last':
                item.update({"isLast": True,})
            else:
                item.update({"isLast": False,})
            item.update({
                "presentationLayoutId": presentation_layout_id,
                "maxTokensPerBlock": 300,
                "maxWordsPerSentence": 15,
                "minWordsPerSentence": 10,
                "forGeneration": True, 
                "isActive": True,
                "presentationLayoutIndexColor": 0
                })
        return slide_layout_frame_data
    

    def update_slide_layout_data(self, presentation_layout_id: str):
        """Create or update fieds in SliedeLayout table."""

        slide_layout_table, session = self.open_session("SlideLayout")

        def logic():
            query = select(slide_layout_table).where(
                slide_layout_table.c.presentationLayoutId == presentation_layout_id
            )
            result = session.execute(query)
            existing_data = result.fetchall()

            cached_data = self.get_slide_layout_data_from_cache(presentation_layout_id)

            for data_item in cached_data:
                uuid_data_item = {
                    k: v if k != 'id' else generate_uuid()
                    for k, v in data_item.items()
                }

                matching_rows = [
                    row for row in existing_data if row.name == uuid_data_item['name']
                ]

                if len(matching_rows) > 0:
                    first_row = matching_rows[0]
                    keys_to_compare = [
                        'number', 'imagesCount', 'maxTokensPerBlock', 'maxWordsPerSentence',
                        'minWordsPerSentence', 'sentences', 'isLast', 'forGeneration',
                        'presentationLayoutIndexColor'
                    ]
                    need_update = False

                    for key in keys_to_compare:
                        if getattr(first_row, key) != uuid_data_item[key]:
                            need_update = True
                            break

                    if need_update:
                        stmt = (
                            update(slide_layout_table).
                            where(slide_layout_table.c.id == first_row.id).
                            values(**uuid_data_item)
                        )
                        session.execute(stmt)
                        session.commit()

                else:
                    new_entry = dict(uuid_data_item)
                    new_entry['id'] = generate_uuid()
                    stmt = insert(slide_layout_table).values(**new_entry)
                    session.execute(stmt)
                    session.commit()

            updated_query = select(slide_layout_table).where(
                slide_layout_table.c.presentationLayoutId == presentation_layout_id
            )
            final_result = session.execute(updated_query)
            return final_result.fetchall()

        return super().execute(logic, session)


if __name__ == '__main__':
#     print(PresentationLayoutManager().select_layout_by_name('classic'))
#     print(PresentationLayoutManager().insert_new_layout('test_12'))
#     print(ColorSettingsManager().select_color_id())
#     print(PresentationLayoutStylesManager().insert_new_ids(id))
#
#     presentation_layout_id = PresentationLayoutManager().insert_new_layout('test_name')
#     print(presentation_layout_id)
#     color_settings_id = ColorSettingsManager().select_color_id()
#     print(color_settings_id)
#     print(PresentationLayoutStylesManager().insert_new_ids(presentation_layout_id, color_settings_id))

    # print(SlideLayoutManager().get_slide_layout_data_from_cache('0197c55e-1c1b-7760-9525-f51752cf23e2'))
    # SlideLayoutManager().get_slide_layout_data_from_cache('0197c55e-1c1b-7760-9525-f51752cf23e2')
    print(SlideLayoutManager().update_slide_layout_data('0197c55e-1c1b-7760-9525-f51752cf23e2'))
    # # classic
    # '019006b0-03af-7b04-a66f-8d31b0a08769'
    # # raif
    # '0197c55e-1c1b-7760-9525-f51752cf23e2'



# poetry run python -m db_work.services