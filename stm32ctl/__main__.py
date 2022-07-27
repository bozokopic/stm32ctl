import sys

from stm32ctl.main import main


if __name__ == '__main__':
    sys.argv[0] = 'stm32ctl'
    sys.exit(main())
