from filters.sal import SalitzkiGolay
from filters.sal_fast import SalitzkiGolayFast

FILTER = {'salitzki_golay' : (SalitzkiGolay, ['height', 'window']),
          'salitzki_golay_fast': (SalitzkiGolayFast,['height', 'window','add_param'])
          }

# Einfach
def get_filter(filter_name, paramter...):
    return FILTER(filter_name)(parameter,....)

# Komplex:

def get_filter_cls_params(filter_name):
    return FILTER(filter_name)


# Code:
# filter_name kommt DYNAMISCH von externen quelle
sal_cls, sal_params_names =  get_filter_cls_params(filter_name)

data['params']

sal_params = []
for par_name in sal_params_names:
    sal_params.append(data['params'][par_name])

sal_filter = sal_cls(*sal_params)





