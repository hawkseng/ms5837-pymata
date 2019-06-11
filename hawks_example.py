#!/usr/bin/python
import ms5837 #Does this mean that every time we see "ms5837" in the code below, that it calls this function?
import time

#sensor = ms5837.MS5837_30BA() # Default I2C bus is 1 (Raspberry Pi 3)
#sensor = ms5837.MS5837_30BA(0) # Specify I2C bus
sensor = ms5837.MS5837_02BA() #This is the correct one to use from the datasheet, however, how can I find the I2C bus info?
#sensor = ms5837.MS5837_02BA(0) #Also, I assume "ms5837" refers to the module, and the MS5837_02BA refers to the class in the module.  What is the point of all of this?
#sensor = ms5837.MS5837(model=ms5837.MS5837_MODEL_30BA, bus=0) # Specify model and bus

# We must initialize the sensor before reading it - I guess this calls the function "init" in the module?
if not sensor.init(): #As far as I can tell, we have never gotten this far in this code.
        print("Sensor could not be initialized")
        exit(1)

# We have to read values from sensor to update pressure and temperature
if not sensor.read():
    print("Sensor read failed!")
    exit(1)

print(("Pressure: %.2f atm  %.2f Torr  %.2f psi") % (
sensor.pressure(ms5837.UNITS_atm),
sensor.pressure(ms5837.UNITS_Torr),
sensor.pressure(ms5837.UNITS_psi))) #I assume these call the function "pressure" in ms5837?  Because of "Sensor.???"

print(("Temperature: %.2f C  %.2f F  %.2f K") % (
sensor.temperature(ms5837.UNITS_Centigrade),
sensor.temperature(ms5837.UNITS_Farenheit),
sensor.temperature(ms5837.UNITS_Kelvin))) #Same as above?

freshwaterDepth = sensor.depth() # default is freshwater
sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)
saltwaterDepth = sensor.depth() # No nead to read() again
sensor.setFluidDensity(1000) # kg/m^3
print(("Depth: %.3f m (freshwater)  %.3f m (saltwater)") % (freshwaterDepth, saltwaterDepth))

# fluidDensity doesn't matter for altitude() (always MSL air density)
print(("MSL Relative Altitude: %.2f m") % sensor.altitude()) # relative to Mean Sea Level pressure in air

time.sleep(5)

# Spew readings
while True:
        if sensor.read(): #This goes to "ms5837" and the "read" function?
                print(("P: %0.1f mbar  %0.3f psi\tT: %0.2f C  %0.2f F") % (
                sensor.pressure(), # Default is mbar (no arguments)
                sensor.pressure(ms5837.UNITS_psi), # Request psi
                sensor.temperature(), # Default is degrees C (no arguments)
                sensor.temperature(ms5837.UNITS_Farenheit))) # Request Farenheit
        else:
                print("Sensor read failed!")
                exit(1)
