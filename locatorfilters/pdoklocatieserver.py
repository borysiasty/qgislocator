from qgis.core import QgsProject, QgsLocatorResult, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPoint, QgsPointXY
from .basefilter import GeocoderFilter
from ..networkaccessmanager import RequestsException

import json

class PdokFilter(GeocoderFilter):

    def __init__(self, iface):
        super().__init__(iface)

    def clone(self):
        return PdokFilter(self.iface)

    def displayName(self):
        return self.tr('PDOK Locatieserver')

    def prefix(self):
        return 'pdok'

    def fetchResults(self, search, context, feedback):
        ##print('--- PdokFilter fetchResults called')
        ##print('PdokFilter search: {}'.format(search))
        ##print('PdokFilter context: {}'.format(context))
        #print('PdokFilter context.targetExtent: {}'.format(context.targetExtent))
        #print('PdokFilter context.targetExtentCrs: {}'.format(context.targetExtentCrs))
        ##print('PdokFilter feedback: {}'.format(feedback))
        self.info(self.tr)
        if len(search) < 3:
            return

        # stripping the search string here to be able to see two geocoders at once and Nominatim needs a space on the end
        search = search.strip()
        url = 'https://geodata.nationaalgeoregister.nl/locatieserver/v3/suggest?q={}'.format(search)
        try:
            self.info('{}'.format(url))
            (response, content) = self.nam.request(url)
            ##print('response: {}'.format(response))
            # TODO: check statuscode etc
            ##print('content: {}'.format(content))

            content_string = content.decode('utf-8')
            obj = json.loads(content_string)
            docs = obj['response']['docs']
            for doc in docs:
                ##print(doc)
                result = QgsLocatorResult()
                result.filter = self
                result.displayString = '{} ({})'.format(doc['weergavenaam'], doc['type'])
                result.userData = doc
                self.resultFetched.emit(result)

        except RequestsException:
            # Handle exception
            print('!!!!!!!!!!! EXCEPTION !!!!!!!!!!!!!: \n{}'. format(RequestsException.args))


    def triggerResult(self, result):
        #print('PdokFilter triggerResult called-----')
        ##print(result.displayString)
        ##print(result.userData)

        ##print('triggerResult called, result: {}'.format(result))

        # PDOK Location server return id's which have to picked up then
        id = result.userData['id']
        url = 'https://geodata.nationaalgeoregister.nl/locatieserver/v3/lookup?id={}'.format(id)
        try:
            (response, content) = self.nam.request(url)
            #print('response: {}'.format(response))
            # TODO: check statuscode etc
            #print('content: {}'.format(content))
            content_string = content.decode('utf-8')
            obj = json.loads(content_string)

            found = obj['response']['numFound']
            if found != 1:
                print('XXXXXXXXXXXXXXXXX  numFound != 1')
            else:
                doc = obj['response']['docs'][0]
                point = QgsPoint()
                point.fromWkt(doc['centroide_ll'])
                point_xy = QgsPointXY(point)
                dest_crs = QgsProject.instance().crs()
                results_crs = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.PostgisCrsId)
                transform = QgsCoordinateTransform(results_crs, dest_crs, QgsProject.instance())
                point_xy = transform.transform(point_xy)
                self.iface.mapCanvas().setCenter(point_xy)

                scale_denominator = 10000.0
                # map the result types to generic GeocoderLocator types to determine the zoom
                if doc['type'] == 'adres':
                    scale_denominator = self.ADDRESS
                elif doc['type'] == 'weg':
                    scale_denominator = self.STREET
                elif doc['type'] == 'postcode':
                    scale_denominator = self.ZIP
                elif doc['type'] == 'gemeente':
                    scale_denominator = self.PLACE
                elif doc['type'] == 'woonplaats':
                    scale_denominator = self.CITY
                self.iface.mapCanvas().zoomScale(scale_denominator)
                self.iface.mapCanvas().refresh()

        except RequestsException:
            # Handle exception
            print('!!!!!!!!!!! EXCEPTION !!!!!!!!!!!!!: \n{}'. format(RequestsException.args))
