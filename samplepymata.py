from pymata_aio.pymata3 import PyMata3
from pymata_aio.constants import Constants
from time import sleep

#arduino = PyMata3() # Why don't we do this?  I assume we use the open socket stuff...
#arduino.i2c_config() # or this?
#open socket for control board - this is from Matt
board = PyMata3(ip_address = '192.168.0.177', ip_port=3030, ip_handshake='')

class TSYS01(object): # What is the purpose of making a "class?"
    
    # Registers - Why do these start with underscore?
    _TSYS01_ADDR             = 0x77  
    _TSYS01_RESET            = 0x1E
    _TSYS01_READ             = 0x00
    _TSYS01_PROM_READ        = 0xA0
    _TSYS01_CONVERT          = 0x48
        
    def __init__(self, model=MODEL_30BA):
        self._model = model
        
        try:
            self._board = board
        except:
            self._board = None

            self._temperature = 0
        
    def init(self):
        if board is None:
            "No board!"
            return False

        board.i2c_write_request(_TSYS01_ADDR, [_TSYS01_RESET])
        
        # Wait for reset to complete
        sleep(0.01)
        
        _C = []
        
        # Read calibration values and CRC
        for i in range(7):
            c = []
            board.i2c_read_request(_TSYS01_ADDR, _TSYS01_PROM_READ + (2*i), 2, Constants.I2C_READ)
            board.sleep(0.1)
            data = board.i2c_read_data(_TSYS01_ADDR)
            for j in range(len(data)):
                c.append(hex(data[j])[2:])
                #print(str(hex(data[j])))

                #print(format(data[j],'06x'))
            
            #c =  str(((int(c) & 0xFF) << 8) | (int(c) >> 8))
            #c =  ((hex(int(c)) & 0xFF) << 8) | (hex(int(c)) >> 8)
            output = "0x"
            output += str(c[1])
            output += str(c[0])
            #print(hex(int(output,16)))
            #print(int(output,0))
            finaloutput =  ((int(output,0) & 0xFF) << 8) | ((int(output,0) >> 8))
            print(finaloutput)
            self._C.append(finaloutput)
                        
        crc = (self._C[0] & 0xF000) >> 12
        if crc != self._crc4(self._C):
            print("PROM read error, CRC failed!")
            return False
        
        return True
        
        # Request D1 conversion (temperature)
        board.i2c_write_request(_TSYS01_ADDR, [_TSYS01_CONVERT_D1_256 + 2*oversampling])
    
        # Maximum conversion time increases linearly with oversampling
        # max time (seconds) ~= 2.2e-6(x) where x = OSR = (2^8, 2^9, ..., 2^13)
        # We use 2.5e-6 for some overhead
        sleep(2.5e-6 * 2**(8+oversampling))
        
        #d = self._bus.read_i2c_block_data(self._MS5837_ADDR, self._MS5837_ADC_READ, 3)
        self._board.i2c_read_request(self._MS5837_ADDR, self._MS5837_ADC_READ, 3, Constants.I2C_READ)
        self._board.sleep(0.1)
        d = self._board.i2c_read_data(self._MS5837_ADDR)


        self._D1 = d[0] << 16 | d[1] << 8 | d[2]
        
        # Request D2 conversion (pressure)
        self._board.i2c_write_request(self._MS5837_ADDR, [self._MS5837_CONVERT_D2_256 + 2*oversampling])
        
    
        # As above
        sleep(2.5e-6 * 2**(8+oversampling))
 
        #d = self._bus.read_i2c_block_data(self._MS5837_ADDR, self._MS5837_ADC_READ, 3)
        self._board.i2c_read_request(self._MS5837_ADDR, self._MS5837_ADC_READ, 3, Constants.I2C_READ)
        self._board.sleep(0.1)
        d = self._board.i2c_read_data(self._MS5837_ADDR)

        self._D2 = d[0] << 16 | d[1] << 8 | d[2]

        # Calculate temperature
        # using raw ADC values and internal calibration
        self._calculate()
        
        return True

    # Temperature in requested units
    # default degrees C
    def temperature(self, conversion=UNITS_Centigrade):
        degC = self._temperature / 100.0
        return degC
        
    # Cribbed from datasheet
    def _calculate(self):
        OFFi = 0
        SENSi = 0
        Ti = 0

       self._temperature = 2000+dT*self._C[6]/8388608

        # Second order compensation
        if self._model == MODEL_02BA:
            if (self._temperature/100) < 20: # Low temp
                Ti = (11*dT*dT)/(34359738368)
                OFFi = (31*(self._temperature-2000)*(self._temperature-2000))/8
                SENSi = (63*(self._temperature-2000)*(self._temperature-2000))/32
                
        else:
            if (self._temperature/100) < 20: # Low temp
                Ti = (3*dT*dT)/(8589934592)
                OFFi = (3*(self._temperature-2000)*(self._temperature-2000))/2
                SENSi = (5*(self._temperature-2000)*(self._temperature-2000))/8
                if (self._temperature/100) < -15: # Very low temp
                    OFFi = OFFi+7*(self._temperature+1500)*(self._temperature+1500)
                    SENSi = SENSi+4*(self._temperature+1500)*(self._temperature+1500)
            elif (self._temperature/100) >= 20: # High temp
                Ti = 2*(dT*dT)/(137438953472)
                OFFi = (1*(self._temperature-2000)*(self._temperature-2000))/16
                SENSi = 0
        
        OFF2 = OFF-OFFi
        SENS2 = SENS-SENSi
        
        if self._model == MODEL_02BA:
            self._temperature = (self._temperature-Ti)
            
        else:
            self._temperature = (self._temperature-Ti)
             
           
class TSYS01(TSYS01):
    def __init__(self):
        TSYS01.__init__(self, 1) #What is this doing???
       
