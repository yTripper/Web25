from django.core.management.base import BaseCommand
from books.examples import run_all_examples

class Command(BaseCommand):
    help = 'Демонстрация использования related_name и timezone в Django'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Запуск демонстрации related_name и timezone...')
        )
        
        try:
            run_all_examples()
            self.stdout.write(
                self.style.SUCCESS('Демонстрация успешно завершена!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при выполнении демонстрации: {e}')
            ) 