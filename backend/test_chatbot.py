import unittest

from app.routers.chatbot import handle_message, MessageIn


class ChatbotParsingTests(unittest.TestCase):
    def test_extracts_route_date_and_transport(self):
        response = handle_message(MessageIn(message='I want to travel from Bengaluru to Hyderabad tomorrow'))
        self.assertEqual(response.context['source'], 'Bengaluru')
        self.assertEqual(response.context['destination'], 'Hyderabad')
        self.assertEqual(response.context['date'], 'tomorrow')

    def test_extracts_transport_and_passengers(self):
        response = handle_message(MessageIn(message='Book a bus for 2 passengers'))
        self.assertEqual(response.context['transport'], 'bus')
        self.assertEqual(response.context['passengers'], 2)

    def test_handles_next_weekday_requests(self):
        response = handle_message(MessageIn(message='I need a train to Chennai next Monday'))
        self.assertEqual(response.context['transport'], 'train')
        self.assertEqual(response.context['destination'], 'Chennai')
        self.assertIn('monday', response.context['date'])


if __name__ == '__main__':
    unittest.main()
