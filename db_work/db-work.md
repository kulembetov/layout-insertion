# Presentation Layout Manager ----------------------------------------------------------------------------
PresentationLayoutManager().select_an_entry_from_presentation_layout(name)
Поиск имени по шаблону
input: название шаблона
output: true / falses

PresentationLayoutManager().insert_an_entry_in_presentation_layout(name)
Генерит id. Вставляет в бд id, name
input: название шаблона
output: id str



# Color Settings Manager ---------------------------------------------------------------------------------
ColorSettingsManager().select_id_from_color_settings()
Достает id из таблицы
input: none
output: id str



# Presentation Layout Styles Manager ----------------------------------------------------------------------
PresentationLayoutStylesManager().insert_an_entry_in_presentation_layout_styles(id)
Генерит id.
Вставляет в таблицу id из PresentationLayoutManager().insert_an_entry_in_presentation_layout(name).
Вставляет в таблицу id из ColorSettingsManager().select_id_from_color_settings()
input: id str (которое создано в .insert_an_entry_in_presentation_layout(name))
output: id str
