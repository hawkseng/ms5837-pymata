from pymata_aio.pymata3 import PyMata3
from pymata_aio.constants import Constants
from time import sleep

arduino = PyMata3() # Why don't we do this?
arduino.i2c_config() # or this?

# Models - What are these?!?  The two sensors on board?
MODEL_02BA = 0
MODEL_30BA = 1

# Oversampling options
OSR_256  = 0
OSR_512  = 1
OSR_1024 = 2
OSR_2048 = 3
OSR_4096 = 4
OSR_8192 = 5

class TSYS01(object):
    
    # Registers - Why do these start with underscore?
    _TSYS01_ADDR             = 0x77  
    _TSYS01_RESET            = 0x1E
    _TSYS01_READ             = 0x00
    _TSYS01_PROM_READ        = 0xA0
    _TSYS01_CONVERT          = 0x48
        
    def __init__(self, model=MODEL_30BA):
        self._model = model
        
        try:
            self._board = arduino
        except:
            self._board = None

            self._temperature = 0
        
    def init(self):
        if self._board is None:
            "No board!"
            return False

        self._board.i2c_write_request(self._MS5837_ADDR, [self._MS5837_RESET])
        
        # Wait for reset to complete
        sleep(0.01)
        
        self._C = []
        
        # Read calibration values and CRC
        for i in range(7):
            c = []
            self._board.i2c_read_request(self._MS5837_ADDR, self._MS5837_PROM_READ + (2*i), 2, Constants.I2C_READ)
            self._board.sleep(0.1)
            data = self._board.i2c_read_data(self._MS5837_ADDR)
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
        
    def read(self, oversampling=OSR_8192):
        if self._board is None:
            print("No board!")
            return False
        
        if oversampling < OSR_256 or oversampling > OSR_8192:
            print("Invalid oversampling option!")
            return False
        
        # Request D1 conversion (temperature)
        self._board.i2c_write_request(self._MS5837_ADDR, [self._MS5837_CONVERT_D1_256 + 2*oversampling])
    
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

        # Calculate compensated pressure and temperature
        # using raw ADC values and internal calibration
        self._calculate()
        
        return True
    
    def setFluidDensity(self, denisty):
        self._fluidDensity = denisty
            
    # Temperature in requested units
    # default degrees C
    def temperature(self, conversion=UNITS_Centigrade):
        degC = self._temperature / 100.0
        if conversion == UNITS_Farenheit:
            return (9/5) * degC + 32
        elif conversion == UNITS_Kelvin:
            return degC - 273
        return degC
        
    # Cribbed from datasheet
    def _calculate(self):
        OFFi = 0
        SENSi = 0
        Ti = 0

        dT = self._D2-self._C[5]*256
        if self._model == MODEL_02BA:
            SENS = self._C[1]*65536+(self._C[3]*dT)/128
            OFF = self._C[2]*131072+(self._C[4]*dT)/64
            self._pressure = (self._D1*SENS/(2097152)-OFF)/(32768)
        else:
            SENS = self._C[1]*32768+(self._C[3]*dT)/256
            OFF = self._C[2]*65536+(self._C[4]*dT)/128
            self._pressure = (self._D1*SENS/(2097152)-OFF)/(8192)
        
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
            self._pressure = (((self._D1*SENS2)/2097152-OFF2)/32768)/100.0
        else:
            self._temperature = (self._temperature-Ti)
            self._pressure = (((self._D1*SENS2)/2097152-OFF2)/8192)/10.0   
        
    # Cribbed from datasheet
    def _crc4(self, n_prom):
        n_rem = 0
        
        n_prom[0] = ((n_prom[0]) & 0x0FFF)
        n_prom.append(0)
    
        for i in range(16):
            if i%2 == 1:
                n_rem ^= ((n_prom[i>>1]) & 0x00FF)
            else:
                n_rem ^= (n_prom[i>>1] >> 8)
                
            for n_bit in range(8,0,-1):
                if n_rem & 0x8000:
                    n_rem = (n_rem << 1) ^ 0x3000
                else:
                    n_rem = (n_rem << 1)

        n_rem = ((n_rem >> 12) & 0x000F)
        
        self.n_prom = n_prom
        self.n_rem = n_rem
    
        return n_rem ^ 0x00
    
class MS5837_30BA(MS5837):
    def __init__(self):
        MS5837.__init__(self, MODEL_30BA)
        
class MS5837_02BA(MS5837):
    def __init__(self):
        MS5837.__init__(self, MODEL_02BA)
