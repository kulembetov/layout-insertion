# Presentation Layout Manager ----------------------------------------------------------------------------
PresentationLayoutManager().select_layout_by_name(name)
Поиск имени по шаблону
input: название шаблона
output: true / falses

PresentationLayoutManager().insert_new_layout(name)
Генерит id. Вставляет в бд id, name
input: название шаблона
output: id str



# Color Settings Manager ---------------------------------------------------------------------------------
ColorSettingsManager().select_color_id()
Достает id из таблицы
input: none
output: id str



# Presentation Layout Styles Manager ----------------------------------------------------------------------
PresentationLayoutStylesManager().insert_new_ids(id)
Генерит id.
Вставляет в таблицу id из PresentationLayoutManager().insert_new_layout(name).
Вставляет в таблицу id из ColorSettingsManager().select_color_id()
input: id str (которое создано в .insert_new_layout(name))
output: id str
