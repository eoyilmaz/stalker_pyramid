# -*- coding: utf-8 -*-

from pyramid.view import view_config
from stalker import Tag


@view_config(
    route_name='get_tags',
    renderer='json',
    permission='Read_Tag'
)
def get_tags(request):
    """returns all the tags in database
    """
    as_list = request.params.get('as_list')
    if as_list:
        return [
            tag.name
            for tag in Tag.query.all()
        ]
    else:
        return [
            {
                'name': tag.name,
                'id': tag.id
            }
            for tag in Tag.query.all()
        ]
