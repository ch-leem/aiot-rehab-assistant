// include/wifi_manager.h
#pragma once
#include <Arduino.h>

void wifi_connect_blocking();
void wifi_ensure_connected();
bool wifi_is_connected();
